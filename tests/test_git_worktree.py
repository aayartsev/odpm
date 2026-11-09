"""Tests for ADR-028 bare mirrors + per-tenant worktrees."""

from __future__ import annotations

from dev_project.host.ports import BootstrapHandle

import fcntl
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from dev_project.config.git_repos import GitRepoCoordinator
from dev_project.errors import ConfigError, GitError
from dev_project.git.build_date import BuildDateResolver
from dev_project.git.checkout import CheckoutService
from dev_project.git.link import HandleOdooProjectLink
from dev_project.git.runner import GitRunner
from dev_project.git.service_sources import (
    collect_service_source_paths,
    materialize_one_service_source,
)
from dev_project.git.worktree import (
    _fetch_mirror_target,
    bind_link_to_worktree_layout,
    configure_link_worktree_context,
    ensure_bare_mirror,
    git_worktree_requested,
    head_sha,
    materialize_link_as_worktree,
    mirror_path,
    repo_file_lock,
    repo_key_from_relative_path,
    tenant_id_from_project_dir,
    worktree_path,
)
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.parse_args import parse_cli_args


def _git(cwd: str, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return (result.stdout or "").strip()


def _init_remote_repo(path: str) -> tuple[str, str]:
    os.makedirs(path, exist_ok=True)
    _git(path, "init")
    _git(path, "config", "user.email", "odpm@example.com")
    _git(path, "config", "user.name", "odpm")
    (Path(path) / "README").write_text("one\n", encoding="utf-8")
    _git(path, "add", "README")
    _git(path, "commit", "-m", "first")
    sha1 = _git(path, "rev-parse", "HEAD")
    (Path(path) / "README").write_text("two\n", encoding="utf-8")
    _git(path, "add", "README")
    _git(path, "commit", "-m", "second")
    sha2 = _git(path, "rev-parse", "HEAD")
    return sha1, sha2


class GitWorktreeFlagTests(unittest.TestCase):
    def test_cli_prepare_git_worktree(self) -> None:
        args = parse_cli_args(["prepare", "--git-worktree"])
        self.assertTrue(args.git_worktree)
        self.assertTrue(git_worktree_requested(args))

    def test_cli_up_git_worktree(self) -> None:
        args = parse_cli_args(["up", "--git-worktree", "--no-git-update"])
        self.assertTrue(args.git_worktree)
        self.assertTrue(args.no_git_update)

    def test_env_truthy(self) -> None:
        with mock.patch.dict(os.environ, {"ODPM_GIT_WORKTREE": "1"}, clear=False):
            self.assertTrue(git_worktree_requested(OdpmCliArgs()))

    def test_off_by_default(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "ODPM_GIT_WORKTREE"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(git_worktree_requested(OdpmCliArgs()))


class TenantIdTests(unittest.TestCase):
    def test_basename(self) -> None:
        self.assertEqual(tenant_id_from_project_dir("/tmp/projects/mr-42"), "mr-42")

    def test_rejects_unsafe(self) -> None:
        with self.assertRaises(ConfigError):
            tenant_id_from_project_dir("/tmp/projects/mr 42")
        with self.assertRaises(ConfigError):
            tenant_id_from_project_dir("/tmp/projects/mr@42")


class WorktreeMaterializeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = self._tmpdir.name
        self.remote = os.path.join(self.root, "remote")
        self.projects = os.path.join(self.root, "projects")
        os.makedirs(self.projects)
        self.sha1, self.sha2 = _init_remote_repo(self.remote)
        self.file_url = f"file://{self.remote}"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _link(self, tenant: str, *, commit: str | None = None) -> HandleOdooProjectLink:
        # HTTP parse for relative_path; override gitlink to the local repo path.
        link = HandleOdooProjectLink(
            "https://example.com/org/demo.git",
            "",
            self.projects,
            system_type="standart",
        )
        link.gitlink = self.remote
        configure_link_worktree_context(
            link,
            tenant=tenant,
            skip_git_update=False,
        )
        if commit:
            link.commit = commit
            link.commit_explicit = True
        return link

    def test_file_url_stays_classic(self) -> None:
        link = HandleOdooProjectLink(
            self.file_url,
            "",
            self.projects,
            system_type="standart",
        )
        configure_link_worktree_context(
            link, tenant="mr-1", skip_git_update=False
        )
        self.assertFalse(link.worktree_mode)

    def test_one_tenant_bare_and_worktree(self) -> None:
        link = self._link("mr-1", commit=self.sha2)
        path = materialize_link_as_worktree(link)
        repo_key = repo_key_from_relative_path(link.project_data.relative_path)
        mirror = mirror_path(self.projects, repo_key)
        self.assertTrue(os.path.isdir(mirror))
        self.assertEqual(path, worktree_path(self.projects, "mr-1", repo_key))
        self.assertEqual(head_sha(link, path), self.sha2)
        self.assertEqual((Path(path) / "README").read_text(encoding="utf-8"), "two\n")

    def test_two_tenants_same_pin(self) -> None:
        a = self._link("mr-a", commit=self.sha2)
        b = self._link("mr-b", commit=self.sha2)
        path_a = materialize_link_as_worktree(a)
        path_b = materialize_link_as_worktree(b)
        self.assertNotEqual(path_a, path_b)
        self.assertEqual(head_sha(a, path_a), self.sha2)
        self.assertEqual(head_sha(b, path_b), self.sha2)
        repo_key = repo_key_from_relative_path(a.project_data.relative_path)
        self.assertTrue(os.path.isdir(mirror_path(self.projects, repo_key)))

    def test_reuse_same_sha(self) -> None:
        link = self._link("mr-1", commit=self.sha2)
        path1 = materialize_link_as_worktree(link)
        mtime = os.path.getmtime(path1)
        path2 = materialize_link_as_worktree(link)
        self.assertEqual(path1, path2)
        self.assertEqual(os.path.getmtime(path2), mtime)

    def test_recreate_on_new_commit(self) -> None:
        link = self._link("mr-1", commit=self.sha1)
        path = materialize_link_as_worktree(link)
        self.assertEqual(head_sha(link, path), self.sha1)
        link.commit = self.sha2
        link.commit_explicit = True
        materialize_link_as_worktree(link)
        self.assertEqual(head_sha(link, path), self.sha2)
        self.assertEqual((Path(path) / "README").read_text(encoding="utf-8"), "two\n")

    def test_no_git_update_missing_raises(self) -> None:
        link = self._link("mr-1", commit=self.sha2)
        link.worktree_skip_update = True
        with self.assertRaises(ConfigError):
            materialize_link_as_worktree(link)

    def test_no_git_update_sha_mismatch_raises(self) -> None:
        link = self._link("mr-1", commit=self.sha1)
        materialize_link_as_worktree(link)
        link.commit = self.sha2
        link.commit_explicit = True
        link.worktree_skip_update = True
        with self.assertRaises(ConfigError):
            materialize_link_as_worktree(link)

    def test_no_git_update_same_sha_ok(self) -> None:
        link = self._link("mr-1", commit=self.sha2)
        materialize_link_as_worktree(link)
        link.worktree_skip_update = True
        path = materialize_link_as_worktree(link)
        self.assertEqual(head_sha(link, path), self.sha2)

    def test_classic_clone_dir_untouched(self) -> None:
        classic = os.path.join(self.projects, "example.com", "org", "demo")
        os.makedirs(classic)
        (Path(classic) / "KEEP").write_text("keep\n", encoding="utf-8")
        link = self._link("mr-1", commit=self.sha2)
        materialize_link_as_worktree(link)
        self.assertTrue((Path(classic) / "KEEP").is_file())

    def test_lock_blocks_second_exclusive_holder(self) -> None:
        lock = os.path.join(self.projects, "demo.lock")
        held = threading.Event()
        release = threading.Event()
        errors: list[BaseException] = []

        def holder() -> None:
            try:
                with repo_file_lock(lock):
                    held.set()
                    release.wait(timeout=5)
            except BaseException as exc:  # noqa: BLE001 — collect for main thread
                errors.append(exc)

        thread = threading.Thread(target=holder)
        thread.start()
        self.assertTrue(held.wait(timeout=5))
        fd = os.open(lock, os.O_RDWR)
        try:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)
            release.set()
            thread.join(timeout=5)
        self.assertFalse(errors)

    def test_configure_binds_project_path_to_worktree_layout(self) -> None:
        link = HandleOdooProjectLink(
            "https://example.com/org/demo.git",
            "",
            self.projects,
            system_type="standart",
        )
        classic = link.project_path
        configure_link_worktree_context(
            link, tenant="mr-1", skip_git_update=False
        )
        repo_key = repo_key_from_relative_path(link.project_data.relative_path)
        expected = worktree_path(self.projects, "mr-1", repo_key)
        self.assertEqual(link.project_path, expected)
        self.assertNotEqual(link.project_path, classic)
        self.assertTrue(link.worktree_mode)

    def test_ensure_present_uses_worktree_paths(self) -> None:
        link = self._link("mr-1", commit=self.sha2)
        wt = materialize_link_as_worktree(link)
        # Simulate a fresh AssembledProject after bootstrap: classic odoo_src_dir is wrong,
        # but the link is worktree-enabled and the worktree exists on disk.
        platform = HandleOdooProjectLink(
            "https://example.com/org/demo.git",
            "",
            self.projects,
            system_type="platform",
        )
        configure_link_worktree_context(
            platform, tenant="mr-1", skip_git_update=True
        )
        developing = HandleOdooProjectLink(
            "https://example.com/org/demo.git",
            "",
            self.projects,
            system_type="standart",
        )
        configure_link_worktree_context(
            developing, tenant="mr-1", skip_git_update=True
        )
        config = mock.MagicMock()
        config.arguments = OdpmCliArgs(git_worktree=True, no_git_update=True)
        config.project_dir = os.path.join(self.root, "mr-1")
        config.user_env = mock.MagicMock(
            path_to_ssh_key="", odoo_projects_dir=self.projects
        )
        config.skip_git_update = mock.MagicMock(return_value=True)
        config.odoo_platform_project = platform
        config.developing_project = developing
        # Classic paths that do not exist — must not be what we check.
        config.odoo_src_dir = os.path.join(self.projects, "example.com", "org", "demo")
        config.developing_project_dir_path = config.odoo_src_dir
        self.assertFalse(os.path.isdir(config.odoo_src_dir))

        GitRepoCoordinator(config, paths=mock.MagicMock()).ensure_git_repos_present()

        self.assertEqual(config.odoo_src_dir, wt)
        self.assertEqual(config.developing_project_dir_path, wt)

    def test_ensure_present_missing_worktree_raises(self) -> None:
        platform = HandleOdooProjectLink(
            "https://example.com/org/demo.git",
            "",
            self.projects,
            system_type="platform",
        )
        configure_link_worktree_context(
            platform, tenant="mr-missing", skip_git_update=True
        )
        config = mock.MagicMock()
        config.arguments = OdpmCliArgs(git_worktree=True, no_git_update=True)
        config.project_dir = os.path.join(self.root, "mr-missing")
        config.user_env = mock.MagicMock(
            path_to_ssh_key="", odoo_projects_dir=self.projects
        )
        config.skip_git_update = mock.MagicMock(return_value=True)
        config.odoo_platform_project = platform
        config.developing_project = platform
        config.odoo_src_dir = "/nope"
        config.developing_project_dir_path = "/nope"

        with self.assertRaises(ConfigError):
            GitRepoCoordinator(config, paths=mock.MagicMock()).ensure_git_repos_present()

    def test_bind_link_noop_when_not_worktree(self) -> None:
        link = HandleOdooProjectLink(
            f"file://{self.remote}",
            "",
            self.projects,
            system_type="standart",
        )
        before = link.project_path
        self.assertIsNone(bind_link_to_worktree_layout(link))
        self.assertEqual(link.project_path, before)

    def test_build_date_ensure_branch_and_deepen_use_bare_cwd(self) -> None:
        link = self._link("mr-1", commit=self.sha2)
        materialize_link_as_worktree(link)
        mirror = link.worktree_mirror
        self.assertTrue(mirror and os.path.isdir(mirror))
        link.commit_explicit = False
        link.commit = ""
        link.branch = "master"
        link.branch_explicit = True
        # Local repo may only have "master" after init; tip SHA is sha2.
        runner = GitRunner(link)
        checkout = CheckoutService(link, runner)
        resolver = BuildDateResolver(link, runner, checkout)

        ensure_cwds: list[str | None] = []
        deepen_cwds: list[str | None] = []

        original_ensure = checkout.ensure_branch_exists

        def track_ensure(branch, odoo_version, *, cwd=None):
            ensure_cwds.append(cwd)
            return original_ensure(branch, odoo_version, cwd=cwd)

        def fake_fetch_history(branch, build_date):
            deepen_cwds.append(resolver._fetch_cwd())

        with mock.patch.object(
            checkout, "ensure_branch_exists", side_effect=track_ensure
        ):
            with mock.patch.object(
                resolver,
                "resolve_commit_with_fetch",
                return_value=self.sha2,
            ):
                with mock.patch.object(
                    resolver,
                    "fetch_history_for_build_date",
                    side_effect=fake_fetch_history,
                ):
                    resolver.apply_build_date("20990101", "master")

        self.assertEqual(ensure_cwds, [mirror])
        # fetch_history not called when resolve_commit_with_fetch is mocked;
        # assert _fetch_cwd itself prefers bare.
        self.assertEqual(resolver._fetch_cwd(), mirror)

    def test_fetch_history_deepen_cwd_is_bare(self) -> None:
        link = self._link("mr-1", commit=self.sha2)
        materialize_link_as_worktree(link)
        mirror = link.worktree_mirror
        runner = GitRunner(link)
        checkout = CheckoutService(link, runner)
        resolver = BuildDateResolver(link, runner, checkout)
        seen: list[str] = []

        def fake_run_git(args, *, cwd=None, capture=True):
            seen.append(cwd or "")
            return mock.MagicMock(returncode=0, stdout="", stderr="")

        with mock.patch.object(runner, "run_git", side_effect=fake_run_git):
            resolver.fetch_history_for_build_date("master", "20990101")

        self.assertTrue(seen)
        self.assertTrue(all(cwd == mirror for cwd in seen))


class ServiceSourcesWorktreeTests(unittest.TestCase):
    def test_materialize_uses_worktree_not_service_sources_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            remote = os.path.join(tmp, "remote")
            projects = os.path.join(tmp, "projects")
            os.makedirs(projects)
            _init_remote_repo(remote)
            sha = _git(remote, "rev-parse", "HEAD")

            project_link = HandleOdooProjectLink(
                "https://example.com/org/sidecar.git",
                "",
                projects,
                system_type="standart",
            )
            project_link.gitlink = remote
            configure_link_worktree_context(
                project_link, tenant="mr-42", skip_git_update=False
            )
            project_link.commit = sha
            project_link.commit_explicit = True

            config = mock.MagicMock()
            config.arguments = OdpmCliArgs(git_worktree=True)
            config.project_dir = os.path.join(tmp, "mr-42")
            config.user_env.odoo_projects_dir = projects
            config.user_env.path_to_ssh_key = ""
            config.skip_git_update.return_value = False
            config.project_settings.odoo_version = "17.0"
            config.user_settings.clean_git_repos = False
            config.user_settings.update_git_repos = False
            config._git_repos.handle_git_link.return_value = project_link

            path = materialize_one_service_source(
                BootstrapHandle(_assembled=config),
                "sidecar",
                "https://example.com/org/sidecar.git",
            )
            repo_key = repo_key_from_relative_path(
                project_link.project_data.relative_path
            )
            expected = worktree_path(projects, "mr-42", repo_key)
            self.assertEqual(path, expected)
            self.assertFalse(
                os.path.isdir(os.path.join(projects, "service-sources", "sidecar"))
            )
            self.assertTrue(os.path.isdir(expected))

    def test_collect_paths_worktree_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = os.path.join(tmp, "projects")
            os.makedirs(projects)
            project_link = HandleOdooProjectLink(
                "https://example.com/org/sidecar.git",
                "",
                projects,
                system_type="standart",
            )
            config = mock.MagicMock()
            config.arguments = OdpmCliArgs(git_worktree=True)
            config.project_dir = os.path.join(tmp, "mr-7")
            config.user_env.odoo_projects_dir = projects
            config.user_env.path_to_ssh_key = ""
            config.bootstrap.manifest_view.service_sources = {
                "sidecar": "https://example.com/org/sidecar.git",
            }
            config._git_repos.handle_git_link.return_value = project_link

            paths = collect_service_source_paths(BootstrapHandle(_assembled=config))
            repo_key = repo_key_from_relative_path(
                project_link.project_data.relative_path
            )
            self.assertEqual(
                paths["sidecar"],
                worktree_path(projects, "mr-7", repo_key),
            )


class NarrowMirrorFetchArgvTests(unittest.TestCase):
    """Assert narrow fetch argv: no all-heads / --tags (ADR-028 amendment)."""

    def _link(self, **kwargs) -> HandleOdooProjectLink:
        link = HandleOdooProjectLink(
            "https://example.com/org/demo.git",
            "",
            "/tmp/projects",
            system_type="standart",
        )
        link.gitlink = "https://example.com/org/demo.git"
        link.commit_explicit = False
        link.branch_explicit = False
        link.commit = ""
        link.branch = ""
        for key, value in kwargs.items():
            setattr(link, key, value)
        return link

    def _capture_fetch_args(self, link, *, odoo_version=None):
        seen: list[list[str]] = []

        def fake_run_git(lnk, args, *, cwd, capture=True, check=False):
            seen.append(list(args))
            return mock.MagicMock(returncode=0, stdout="", stderr="")

        with mock.patch(
            "dev_project.git.worktree._run_git", side_effect=fake_run_git
        ):
            _fetch_mirror_target(
                link, mirror="/mirrors/demo.git", odoo_version=odoo_version
            )
        return seen

    def test_tip_fetch_has_no_wide_refspec(self) -> None:
        link = self._link()
        seen = self._capture_fetch_args(link)
        self.assertEqual(seen, [["fetch", "--depth", "1", "origin"]])
        joined = " ".join(seen[0])
        self.assertNotIn("+refs/heads/*", joined)
        self.assertNotIn("--tags", joined)

    def test_tip_falls_back_to_head(self) -> None:
        link = self._link()
        seen: list[list[str]] = []
        calls = {"n": 0}

        def fake_run_git(lnk, args, *, cwd, capture=True, check=False):
            seen.append(list(args))
            calls["n"] += 1
            code = 1 if calls["n"] == 1 else 0
            return mock.MagicMock(returncode=code, stdout="", stderr="")

        with mock.patch(
            "dev_project.git.worktree._run_git", side_effect=fake_run_git
        ):
            _fetch_mirror_target(link, mirror="/mirrors/demo.git")
        self.assertEqual(
            seen,
            [
                ["fetch", "--depth", "1", "origin"],
                ["fetch", "--depth", "1", "origin", "HEAD"],
            ],
        )

    def test_commit_fetch_includes_sha(self) -> None:
        sha = "abc123def456"
        link = self._link(commit=sha, commit_explicit=True)
        seen = self._capture_fetch_args(link)
        self.assertEqual(seen, [["fetch", "--depth", "1", "origin", sha]])

    def test_commit_fetch_failure_raises_without_wide_fallback(self) -> None:
        link = self._link(commit="deadbeef", commit_explicit=True)
        seen: list[list[str]] = []

        def fake_run_git(lnk, args, *, cwd, capture=True, check=False):
            seen.append(list(args))
            return mock.MagicMock(returncode=1, stdout="", stderr="")

        with mock.patch(
            "dev_project.git.worktree._run_git", side_effect=fake_run_git
        ):
            with self.assertRaises(GitError):
                _fetch_mirror_target(link, mirror="/mirrors/demo.git")
        self.assertEqual(len(seen), 1)
        self.assertNotIn("+refs/heads/*", " ".join(seen[0]))

    def test_branch_fetch_refspec(self) -> None:
        link = self._link(branch="19.0", branch_explicit=True)
        seen = self._capture_fetch_args(link)
        self.assertEqual(
            seen,
            [
                [
                    "fetch",
                    "--depth",
                    "1",
                    "origin",
                    "+refs/heads/19.0:refs/heads/19.0",
                ]
            ],
        )

    def test_odoo_version_fetch_refspec(self) -> None:
        link = self._link()
        seen = self._capture_fetch_args(link, odoo_version="18.0")
        self.assertEqual(
            seen,
            [
                [
                    "fetch",
                    "--depth",
                    "1",
                    "origin",
                    "+refs/heads/18.0:refs/heads/18.0",
                ]
            ],
        )

    def test_skip_fetch_does_not_call_narrow(self) -> None:
        link = self._link(commit="abc", commit_explicit=True)
        with tempfile.TemporaryDirectory() as tmp:
            mirror = os.path.join(tmp, "demo.git")
            os.makedirs(mirror)
            with mock.patch(
                "dev_project.git.worktree._fetch_mirror_target"
            ) as narrow:
                ensure_bare_mirror(link, mirror=mirror, skip_fetch=True)
                narrow.assert_not_called()

    def test_first_clone_non_platform_uses_depth(self) -> None:
        link = self._link()
        with tempfile.TemporaryDirectory() as tmp:
            mirror = os.path.join(tmp, "mirrors", "demo.git")
            parent = os.path.dirname(mirror)
            os.makedirs(parent)
            clone_cmds: list[list[str]] = []

            def fake_run_logged(cmd, cwd=None):
                clone_cmds.append(list(cmd))
                os.makedirs(mirror)
                return 0

            with mock.patch(
                "dev_project.git.worktree.run_logged", side_effect=fake_run_logged
            ):
                with mock.patch(
                    "dev_project.git.worktree._fetch_mirror_target"
                ) as narrow:
                    ensure_bare_mirror(
                        link, mirror=mirror, skip_fetch=False, odoo_version=None
                    )
                    narrow.assert_called_once()
            self.assertTrue(clone_cmds)
            self.assertIn("--depth", clone_cmds[0])
            self.assertIn("1", clone_cmds[0])
            self.assertIn("--bare", clone_cmds[0])


if __name__ == "__main__":
    unittest.main()
