import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.git.deps_lock import DepsLock, LockEntry, load_deps_lock, save_deps_lock
from dev_project.git.deps_lock_manager import DepsLockManager


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
    link.get_project_path = MagicMock(return_value=overrides.get("project_path", "/tmp/repo"))
    link.resolve_head_sha.return_value = overrides.get(
        "head_sha", "cccccccccccccccccccccccccccccccccccccccc"
    )
    return link


class DepsLockManagerApplyTests(unittest.TestCase):
    def _config(self, project_dir: str):
        config = MagicMock()
        config.project_dir = project_dir
        config.dependencies = [
            "https://github.com/OCA/partner-contact.git",
            "https://github.com/acme/extra.git",
        ]
        config.odoo_platform_project = _bare_link(
            gitlink="https://github.com/odoo/odoo.git",
            branch="19.0",
            branch_explicit=True,
        )
        config.dependencies_projects = [
            _bare_link(gitlink="https://github.com/OCA/partner-contact.git"),
            _bare_link(gitlink="https://github.com/OCA/web.git"),
        ]
        return config

    def test_apply_pins_platform_and_seed_dependencies_only(self):
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
                    )
                ],
            )
            save_deps_lock(
                os.path.join(project_dir, ".odpm", "deps.lock.json"),
                lock,
            )
            config = self._config(project_dir)
            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()
            manager.apply_to_platform(config.odoo_platform_project)
            manager.apply_to_seed_dependencies(config.dependencies_projects)

            platform = config.odoo_platform_project
            self.assertEqual(platform.commit, lock.platform.commit)
            self.assertTrue(platform.commit_explicit)

            partner = config.dependencies_projects[0]
            self.assertEqual(partner.commit, lock.dependencies[0].commit)
            self.assertTrue(partner.commit_explicit)

            oca_web = config.dependencies_projects[1]
            self.assertFalse(oca_web.commit_explicit)
            self.assertTrue(manager.is_pinned(platform))
            self.assertTrue(manager.is_pinned(partner))
            self.assertFalse(manager.is_pinned(oca_web))


class DepsLockManagerCollectTests(unittest.TestCase):
    def test_collect_and_save_writes_platform_and_seed_entries(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies = ["https://github.com/OCA/partner-contact.git"]
            config.odoo_platform_project = _bare_link(
                gitlink="https://github.com/odoo/odoo.git",
                branch="19.0",
                branch_explicit=True,
                head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
            config.dependencies_projects = [
                _bare_link(
                    gitlink="https://github.com/OCA/partner-contact.git",
                    head_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                ),
                _bare_link(
                    gitlink="https://github.com/OCA/web.git",
                    head_sha="dddddddddddddddddddddddddddddddddddddddd",
                ),
            ]

            with patch(
                "dev_project.git.deps_lock_manager.resolve_lock_commit",
                side_effect=lambda link: link.resolve_head_sha(),
            ):
                DepsLockManager(config).collect_and_save()

            lock_path = os.path.join(project_dir, ".odpm", "deps.lock.json")
            loaded = load_deps_lock(lock_path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.platform.commit, "a" * 40)
            self.assertEqual(len(loaded.dependencies), 1)
            self.assertEqual(loaded.dependencies[0].commit, "b" * 40)
            config.odoo_platform_project.resolve_head_sha.assert_called_once()
            config.dependencies_projects[0].resolve_head_sha.assert_called_once()
            config.dependencies_projects[1].resolve_head_sha.assert_not_called()

    def test_collect_and_save_uses_file_snapshot_for_file_platform(self):
        with tempfile.TemporaryDirectory() as project_dir:
            platform_dir = os.path.join(project_dir, "platform")
            odoo_dir = os.path.join(platform_dir, "odoo")
            os.makedirs(odoo_dir)
            Path(odoo_dir, "release.py").write_text("v", encoding="utf-8")
            Path(platform_dir, "odoo-bin").write_text("bin", encoding="utf-8")

            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies = []
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
            config.dependencies_projects = []

            DepsLockManager(config).collect_and_save()

            loaded = load_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"))
            assert loaded is not None
            self.assertTrue(loaded.platform.url.startswith("file://"))
            self.assertRegex(loaded.platform.commit, r"^[0-9a-f]{40}$")
            platform.resolve_head_sha.assert_not_called()


class DepsLockManagerModeTests(unittest.TestCase):
    def test_has_platform_lock_false_without_load(self):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        manager = DepsLockManager(config)
        self.assertFalse(manager.has_platform_lock())

    @patch("dev_project.git.deps_lock_manager.load_deps_lock", return_value=None)
    def test_apply_is_noop_without_lock(self, _mock_load):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.odoo_platform_project = _bare_link()
        config.dependencies_projects = []
        manager = DepsLockManager(config)
        manager.load()
        manager.enter_apply_mode()
        manager.apply_to_platform(config.odoo_platform_project)
        self.assertFalse(config.odoo_platform_project.commit_explicit)


if __name__ == "__main__":
    unittest.main()
