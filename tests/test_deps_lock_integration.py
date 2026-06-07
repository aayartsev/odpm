"""Integration tests for deps.lock apply → checkout → verify with real git repos."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from dev_project.errors import PipelineError
from dev_project.git import HandleOdooProjectLink
from dev_project.git.deps_lock import DepsLock, LockEntry, save_deps_lock
from dev_project.git.deps_lock_manager import DepsLockManager
from dev_project.scenario_policy import ScenarioPolicy


def _init_git_repo(path: str, *, content: str = "v1") -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    for command in (
        ["git", "init"],
        ["git", "config", "user.email", "test@test"],
        ["git", "config", "user.name", "test"],
    ):
        subprocess.run(command, cwd=path, check=True, capture_output=True)
    (Path(path) / "README").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_link_at(
    repo_path: str,
    url: str,
    *,
    link_type: str = constants.GITLINK_TYPE_GIT,
) -> HandleOdooProjectLink:
    link = object.__new__(HandleOdooProjectLink)
    link.project_path = repo_path
    link.project_link = url
    link.gitlink = url
    link.project_string = url
    link.branch = ""
    link.branch_explicit = False
    link.commit = ""
    link.commit_explicit = False
    link.link_type = link_type
    link.is_true = True
    link.path_to_ssh_key = ""
    link.dir_to_clone = os.path.dirname(repo_path)
    link.system_type = "standart"
    link._wire_git_services()
    return link


def _config_stub(project_dir: str, scenario: str, **kwargs):
    from unittest.mock import MagicMock

    config = MagicMock()
    config.project_dir = project_dir
    config.policy = ScenarioPolicy.from_scenario(scenario)
    config.seed_dependency_urls = MagicMock(return_value=[])
    config.dependencies = []
    config.dependencies_projects = kwargs.get("dependencies_projects", [])
    config.odoo_platform_project = kwargs["platform"]
    config.developing_project = kwargs.get(
        "developing",
        _git_link_at("/tmp/unused", "file:///tmp/unused", link_type=constants.GITLINK_TYPE_FILE),
    )
    return config


class DepsLockIntegrationTests(unittest.TestCase):
    def test_apply_checkout_verify_passes_with_matching_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            platform_dir = os.path.join(tmp, "platform")
            dep_dir = os.path.join(tmp, "dep")
            platform_url = "https://github.com/test/platform.git"
            dep_url = "https://github.com/test/dep.git"
            platform_sha = _init_git_repo(platform_dir)
            dep_sha = _init_git_repo(dep_dir)

            project_dir = os.path.join(tmp, "project")
            os.makedirs(os.path.join(project_dir, ".odpm"), exist_ok=True)
            lock = DepsLock(
                platform=LockEntry(url=platform_url, commit=platform_sha),
                dependencies=[LockEntry(url=dep_url, commit=dep_sha)],
            )
            save_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"), lock)

            platform = _git_link_at(platform_dir, platform_url)
            dep = _git_link_at(dep_dir, dep_url)
            config = _config_stub(
                project_dir,
                constants.DEVELOPER_SCENARIO,
                platform=platform,
                dependencies_projects=[dep],
            )
            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()
            manager.apply_to_platform(platform)
            manager.apply_to_dependencies([dep])

            self.assertTrue(platform.commit_explicit)
            self.assertEqual(platform.commit, platform_sha)
            self.assertTrue(dep.commit_explicit)
            self.assertEqual(dep.commit, dep_sha)

            platform.checkout_repository("19.0", update_git_repos=False)
            dep.checkout_repository("19.0", update_git_repos=False)

            manager.verify_after_checkout(
                platform=platform,
                developing=config.developing_project,
                dependencies=[dep],
            )

    def test_verify_fails_in_ci_when_checkout_does_not_match_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            platform_dir = os.path.join(tmp, "platform")
            dep_dir = os.path.join(tmp, "dep")
            platform_url = "https://github.com/test/platform.git"
            dep_url = "https://github.com/test/dep.git"
            platform_sha = _init_git_repo(platform_dir)
            dep_sha = _init_git_repo(dep_dir)
            (Path(dep_dir) / "README2").write_text("v2", encoding="utf-8")
            subprocess.run(["git", "add", "README2"], cwd=dep_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "v2"],
                cwd=dep_dir,
                check=True,
                capture_output=True,
            )
            newer_dep_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=dep_dir,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertNotEqual(dep_sha, newer_dep_sha)

            project_dir = os.path.join(tmp, "project")
            os.makedirs(os.path.join(project_dir, ".odpm"), exist_ok=True)
            lock = DepsLock(
                platform=LockEntry(url=platform_url, commit=platform_sha),
                dependencies=[LockEntry(url=dep_url, commit=dep_sha)],
            )
            save_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"), lock)

            platform = _git_link_at(platform_dir, platform_url)
            dep = _git_link_at(dep_dir, dep_url)
            config = _config_stub(
                project_dir,
                constants.CI_SCENARIO,
                platform=platform,
                dependencies_projects=[dep],
            )
            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()
            manager.apply_to_platform(platform)
            manager.apply_to_dependencies([dep])
            platform.checkout_repository("19.0", update_git_repos=False)
            dep.checkout_repository("19.0", update_git_repos=False)
            subprocess.run(
                ["git", "reset", "--hard", newer_dep_sha],
                cwd=dep_dir,
                check=True,
                capture_output=True,
            )

            with self.assertRaises(PipelineError):
                manager.verify_after_checkout(
                    platform=platform,
                    developing=config.developing_project,
                    dependencies=[dep],
                )


if __name__ == "__main__":
    unittest.main()
