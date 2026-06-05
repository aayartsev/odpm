"""
Unit tests for odoo_build_date git resolution.

These tests use a small local git repo (not github.com/odoo/odoo).
They verify date parsing and that depth=1 clone cannot resolve an older
nightly date until history is fetched (--deepen / shallow-since path).

For a real fork, run odpm with --odoo-build-date and check the log line
"Resolved odoo_build_date ... to commit ...".
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dev_project import constants
from dev_project.handle_odoo_project_git_link import HandleOdooProjectLink
from dev_project.inside_docker_app.utils import (
    commit_before_timestamp,
    is_actionable_build_date,
    parse_build_date,
)


def _link_for_repo(repo: Path) -> HandleOdooProjectLink:
    """Minimal HandleOdooProjectLink bound to an existing git directory."""
    link = object.__new__(HandleOdooProjectLink)
    link.project_path = str(repo)
    link.path_to_ssh_key = ""
    link.project_string = str(repo)
    return link


def _git(repo: Path, *args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=kwargs.get("check", True),
        capture_output=True,
        text=True,
        **{k: v for k, v in kwargs.items() if k != "check"},
    )


def _init_repo_with_dated_commits() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="odpm_git_build_date_"))
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@test")
    _git(repo, "config", "user.name", "test")

    base = datetime(2025, 5, 27, 12, 0, 0)
    for offset in range(3):
        day = base + timedelta(days=offset)
        (repo / "file.txt").write_text(f"v{offset}\n", encoding="utf-8")
        _git(repo, "add", "file.txt")
        env = {
            **dict(__import__("os").environ),
            "GIT_AUTHOR_DATE": day.isoformat(),
            "GIT_COMMITTER_DATE": day.isoformat(),
        }
        subprocess.run(
            ["git", "commit", "-m", f"day {offset}"],
            cwd=repo,
            check=True,
            capture_output=True,
            env=env,
        )

    _git(repo, "branch", "-M", "17.0")
    return repo


def _commit_sha(repo: Path, message: str) -> str:
    result = _git(
        repo,
        "log",
        "--all",
        "--grep",
        message,
        "-1",
        "--format=%H",
    )
    sha = result.stdout.strip()
    if not sha:
        raise AssertionError(f"Commit with message {message!r} not found in {repo}")
    return sha


def _shallow_clone(source: Path, dest: Path) -> None:
    """Mimic remote shallow clone; --no-local avoids copying full history from disk."""
    subprocess.run(
        [
            "git",
            "clone",
            "--no-local",
            "--depth",
            str(constants.PLATFORM_GIT_CLONE_DEPTH),
            "-b",
            "17.0",
            str(source),
            str(dest),
        ],
        check=True,
        capture_output=True,
    )


class GitBuildDateTests(unittest.TestCase):
    BUILD_DATE = "20250528"  # last commit on 2025-05-28 → "day 1"

    def test_is_actionable_build_date(self):
        self.assertFalse(is_actionable_build_date(None))
        self.assertFalse(is_actionable_build_date(""))
        self.assertFalse(is_actionable_build_date("latest"))
        self.assertTrue(is_actionable_build_date("20250529"))

    def test_parse_build_date_formats(self):
        self.assertEqual(parse_build_date("20250529"), datetime(2025, 5, 29))
        self.assertEqual(parse_build_date("2025-05-29"), datetime(2025, 5, 29))

    def test_parse_build_date_invalid(self):
        with self.assertRaises(ValueError):
            parse_build_date("not-a-date")

    def test_commit_before_timestamp(self):
        self.assertEqual(commit_before_timestamp("20250529"), "2025-05-30 00:00:00")
        self.assertEqual(commit_before_timestamp("20250528"), "2025-05-29 00:00:00")

    def test_full_repo_resolves_exact_commit_sha(self):
        repo = _init_repo_with_dated_commits()
        try:
            expected = _commit_sha(repo, "day 1")
            resolved = _link_for_repo(repo).resolve_commit_by_build_date(
                "17.0", self.BUILD_DATE
            )
            self.assertEqual(
                resolved,
                expected,
                "full repo must resolve to the May 28 commit (day 1), not HEAD",
            )
        finally:
            shutil.rmtree(repo)

    def test_shallow_clone_head_is_newest_commit(self):
        repo = _init_repo_with_dated_commits()
        shallow = Path(tempfile.mkdtemp(prefix="odpm_shallow_"))
        try:
            _shallow_clone(repo, shallow)
            head = _git(shallow, "rev-parse", "HEAD").stdout.strip()
            newest = _commit_sha(repo, "day 2")
            self.assertEqual(
                head,
                newest,
                "depth=1 clone must point at newest commit (day 2), not the nightly target",
            )
        finally:
            shutil.rmtree(repo)
            shutil.rmtree(shallow)

    def test_shallow_clone_cannot_resolve_older_build_date_without_fetch(self):
        """Proves the fetch/deepen path is required (mimics real Odoo shallow clone)."""
        repo = _init_repo_with_dated_commits()
        shallow = Path(tempfile.mkdtemp(prefix="odpm_shallow_"))
        try:
            _shallow_clone(repo, shallow)
            with self.assertRaises(RuntimeError) as ctx:
                _link_for_repo(shallow).resolve_commit_by_build_date(
                    "17.0", self.BUILD_DATE
                )
            self.assertIn("No commit", str(ctx.exception))
        finally:
            shutil.rmtree(repo)
            shutil.rmtree(shallow)

    def test_resolve_commit_with_fetch_matches_full_repo_sha(self):
        repo = _init_repo_with_dated_commits()
        shallow = Path(tempfile.mkdtemp(prefix="odpm_shallow_"))
        try:
            expected = _commit_sha(repo, "day 1")
            _shallow_clone(repo, shallow)

            resolved = _link_for_repo(shallow).resolve_commit_with_fetch(
                "17.0", self.BUILD_DATE
            )
            self.assertEqual(resolved, expected)

            message = _git(
                shallow, "log", "-1", "--format=%ci %s", resolved
            ).stdout.strip()
            self.assertIn("day 1", message)
        finally:
            shutil.rmtree(repo)
            shutil.rmtree(shallow)

    def test_resolve_commit_with_fetch_invokes_fetch_when_needed(self):
        repo = _init_repo_with_dated_commits()
        shallow = Path(tempfile.mkdtemp(prefix="odpm_shallow_"))
        try:
            _shallow_clone(repo, shallow)
            real_fetch = HandleOdooProjectLink._fetch_history_for_build_date
            with mock.patch.object(
                HandleOdooProjectLink,
                "_fetch_history_for_build_date",
                autospec=True,
                side_effect=lambda self, branch, build_date: real_fetch(
                    self, branch, build_date
                ),
            ) as fetch_mock:
                _link_for_repo(shallow).resolve_commit_with_fetch(
                    "17.0", self.BUILD_DATE
                )
            fetch_mock.assert_called_once()
        finally:
            shutil.rmtree(repo)
            shutil.rmtree(shallow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
