import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.errors import PipelineError
from dev_project.git.deps_lock import DepsLock, LockEntry, load_deps_lock, save_deps_lock
from dev_project.git.deps_lock_manager import DepsLockManager
from dev_project.scenario_policy import ScenarioPolicy


def _bare_link(**overrides):
    link = MagicMock()
    link.gitlink = overrides.get("gitlink", "https://github.com/acme/demo.git")
    link.project_link = overrides.get("project_link", link.gitlink)
    link.project_string = overrides.get("project_string", link.gitlink)
    link.branch = overrides.get("branch", "")
    link.branch_explicit = overrides.get("branch_explicit", False)
    link.commit_explicit = overrides.get("commit_explicit", False)
    link.commit = overrides.get("commit", "")
    link.link_type = overrides.get("link_type", constants.GITLINK_TYPE_GIT)
    link.is_true = overrides.get("is_true", True)
    link.get_project_path = MagicMock(return_value=overrides.get("project_path", "/tmp/repo"))
    link.resolve_head_sha.return_value = overrides.get(
        "head_sha", "cccccccccccccccccccccccccccccccccccccccc"
    )
    return link


def _config_with_policy(project_dir: str, scenario: str, **overrides):
    config = MagicMock()
    config.project_dir = project_dir
    config.policy = ScenarioPolicy.from_scenario(scenario)
    config.dependencies = overrides.get(
        "dependencies",
        ["https://github.com/OCA/partner-contact.git"],
    )
    config._raw_odpm_json = overrides.get(
        "_raw_odpm_json",
        {"dependencies": ["https://github.com/OCA/partner-contact.git"]},
    )
    config.odoo_platform_project = overrides.get(
        "odoo_platform_project",
        _bare_link(
            gitlink="https://github.com/odoo/odoo.git",
            branch="19.0",
            branch_explicit=True,
        ),
    )
    config.dependencies_projects = overrides.get(
        "dependencies_projects",
        [
            _bare_link(gitlink="https://github.com/OCA/partner-contact.git"),
            _bare_link(gitlink="git@github.com:OCA/web.git"),
        ],
    )
    config.developing_project = overrides.get(
        "developing_project",
        _bare_link(gitlink="https://github.com/acme/developing.git"),
    )
    return config


class DepsLockManagerApplyTests(unittest.TestCase):
    def test_apply_pins_platform_and_all_lock_dependencies(self):
        with tempfile.TemporaryDirectory() as project_dir:
            lock = DepsLock(
                platform=LockEntry(
                    url="https://github.com/odoo/odoo",
                    commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    branch="19.0",
                ),
                dependencies=[
                    LockEntry(
                        url="https://github.com/OCA/partner-contact",
                        commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    ),
                    LockEntry(
                        url="https://github.com/OCA/web",
                        commit="dddddddddddddddddddddddddddddddddddddddd",
                    ),
                ],
            )
            save_deps_lock(
                os.path.join(project_dir, ".odpm", "deps.lock.json"),
                lock,
            )
            config = _config_with_policy(project_dir, constants.DEVELOPER_SCENARIO)
            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()
            manager.apply_to_platform(config.odoo_platform_project)
            manager.apply_to_dependencies(config.dependencies_projects)

            self.assertTrue(config.odoo_platform_project.commit_explicit)
            self.assertTrue(config.dependencies_projects[0].commit_explicit)
            self.assertTrue(config.dependencies_projects[1].commit_explicit)

    def test_apply_to_developing_skips_file_link(self):
        with tempfile.TemporaryDirectory() as project_dir:
            lock = DepsLock(
                platform=LockEntry(
                    url="https://github.com/odoo/odoo",
                    commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                ),
                developing=LockEntry(
                    url="https://github.com/acme/developing",
                    commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                ),
            )
            save_deps_lock(
                os.path.join(project_dir, ".odpm", "deps.lock.json"),
                lock,
            )
            config = _config_with_policy(project_dir, constants.DEVELOPER_SCENARIO)
            config.developing_project = _bare_link(
                project_link="file:///tmp/local-dev",
                link_type=constants.GITLINK_TYPE_FILE,
            )
            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()
            manager.apply_to_developing(config.developing_project)
            self.assertFalse(config.developing_project.commit_explicit)


class DepsLockManagerCollectTests(unittest.TestCase):
    def test_collect_and_save_writes_all_resolved_dependencies_sorted(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = _config_with_policy(project_dir, constants.DEVELOPER_SCENARIO)
            config.odoo_platform_project = _bare_link(
                gitlink="https://github.com/odoo/odoo.git",
                branch="19.0",
                branch_explicit=True,
                head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )

            with patch(
                "dev_project.git.deps_lock_manager.resolve_lock_commit",
                side_effect=lambda link: link.resolve_head_sha(),
            ):
                DepsLockManager(config).collect_and_save(
                    developing=config.developing_project,
                )

            loaded = load_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"))
            assert loaded is not None
            self.assertEqual(len(loaded.dependencies), 2)
            self.assertEqual(loaded.dependencies[0].url, "https://github.com/OCA/partner-contact")
            self.assertIsNotNone(loaded.developing)

    def test_collect_and_save_uses_file_snapshot_for_file_platform(self):
        with tempfile.TemporaryDirectory() as project_dir:
            platform_dir = os.path.join(project_dir, "platform")
            odoo_dir = os.path.join(platform_dir, "odoo")
            os.makedirs(odoo_dir)
            Path(odoo_dir, "release.py").write_text("v", encoding="utf-8")
            Path(platform_dir, "odoo-bin").write_text("bin", encoding="utf-8")

            config = _config_with_policy(project_dir, constants.DEVELOPER_SCENARIO)
            config.dependencies = []
            config.dependencies_projects = []
            config._raw_odpm_json = {"dependencies": []}
            platform = MagicMock()
            platform.gitlink = ""
            platform.project_link = f"file://{platform_dir}"
            platform.project_string = platform.project_link
            platform.branch_explicit = False
            platform.commit_explicit = False
            platform.commit = ""
            platform.link_type = constants.GITLINK_TYPE_FILE
            platform.get_project_path.return_value = platform_dir
            config.odoo_platform_project = platform
            config.developing_project = _bare_link(
                project_link="file:///tmp/dev",
                link_type=constants.GITLINK_TYPE_FILE,
            )

            DepsLockManager(config).collect_and_save(developing=config.developing_project)

            loaded = load_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"))
            assert loaded is not None
            self.assertEqual(loaded.platform.kind, "file")
            platform.resolve_head_sha.assert_not_called()
            self.assertIsNone(loaded.developing)


class DepsLockManagerVerifyTests(unittest.TestCase):
    def test_verify_after_checkout_warns_in_developer_scenario(self):
        config = _config_with_policy("/tmp/project", constants.DEVELOPER_SCENARIO)
        lock = DepsLock(
            platform=LockEntry(
                url="https://github.com/odoo/odoo",
                commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ),
        )
        manager = DepsLockManager(config)
        manager._lock = lock
        manager._apply_mode = True
        config.odoo_platform_project.resolve_head_sha.return_value = "b" * 40

        with self.assertLogs("dev_project.git.deps_lock_manager", level="WARNING"):
            manager.verify_after_checkout(
                platform=config.odoo_platform_project,
                developing=config.developing_project,
                dependencies=config.dependencies_projects,
            )

    def test_verify_after_checkout_fails_in_ci_scenario(self):
        config = _config_with_policy("/tmp/project", constants.CI_SCENARIO)
        lock = DepsLock(
            platform=LockEntry(
                url="https://github.com/odoo/odoo",
                commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ),
        )
        manager = DepsLockManager(config)
        manager._lock = lock
        manager._apply_mode = True
        config.odoo_platform_project.resolve_head_sha.return_value = "b" * 40

        with self.assertRaises(PipelineError):
            manager.verify_after_checkout(
                platform=config.odoo_platform_project,
                developing=config.developing_project,
                dependencies=config.dependencies_projects,
            )

    def test_missing_seed_in_lock_fails_ci(self):
        config = _config_with_policy("/tmp/project", constants.CI_SCENARIO)
        config._raw_odpm_json = {
            "dependencies": ["https://github.com/OCA/missing.git"]
        }
        lock = DepsLock(
            platform=LockEntry(
                url="https://github.com/odoo/odoo",
                commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ),
            dependencies=[],
        )
        manager = DepsLockManager(config)
        manager._lock = lock
        manager._apply_mode = True

        with self.assertRaises(PipelineError):
            manager.apply_to_dependencies([])


class DepsLockManagerModeTests(unittest.TestCase):
    def test_has_platform_lock_false_without_load(self):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        manager = DepsLockManager(config)
        self.assertFalse(manager.has_platform_lock())

    @patch("dev_project.git.deps_lock_manager.load_deps_lock", return_value=None)
    def test_apply_is_noop_without_lock(self, _mock_load):
        config = _config_with_policy("/tmp/project", constants.DEVELOPER_SCENARIO)
        manager = DepsLockManager(config)
        manager.load()
        manager.enter_apply_mode()
        manager.apply_to_platform(config.odoo_platform_project)
        self.assertFalse(config.odoo_platform_project.commit_explicit)


if __name__ == "__main__":
    unittest.main()
