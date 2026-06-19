"""Tests for manifest locks.git ↔ deps.lock sync."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.git.deps_lock import DepsLock, LockEntry
from dev_project.git.deps_lock_manager import DepsLockManager
from dev_project.manifest.locks import (
    LockSource,
    deps_lock_from_manifest_git_locks,
    git_locks_map_from_deps_lock,
    lookup_git_lock_commit,
    manifest_locks_from_deps_lock,
    resolve_lock_source,
)
from dev_project.manifest.reader import ManifestView


class GitLocksMapTests(unittest.TestCase):
    def test_round_trip_deps_lock(self):
        lock = DepsLock(
            platform=LockEntry(
                url="https://github.com/odoo/odoo.git",
                commit="c" * 40,
            ),
            dependencies=[
                LockEntry(
                    url="https://github.com/OCA/web.git",
                    commit="d" * 40,
                )
            ],
        )
        manifest_locks = manifest_locks_from_deps_lock(lock)
        restored = deps_lock_from_manifest_git_locks(
            manifest_locks["git"],
            platform_git_link="https://github.com/odoo/odoo.git 17.0",
            developing_git_link=None,
            dependency_git_links=["https://github.com/OCA/web.git 17.0"],
        )
        self.assertEqual(restored.platform.commit, "c" * 40)
        self.assertEqual(restored.dependencies[0].commit, "d" * 40)
        self.assertEqual(git_locks_map_from_deps_lock(lock), manifest_locks["git"])

    def test_lookup_matches_canonical_url(self):
        locks = {"https://github.com/odoo/odoo.git": "e" * 40}
        self.assertEqual(
            lookup_git_lock_commit(
                locks,
                "https://github.com/odoo/odoo.git 17.0",
            ),
            "e" * 40,
        )


class ResolveLockSourceTests(unittest.TestCase):
    def test_prefers_manifest_on_v2_with_locks(self):
        config = MagicMock()
        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm="4.4",
            raw_normalized={},
            locks={"git": {"https://github.com/odoo/odoo.git": "f" * 40}},
        )
        self.assertEqual(resolve_lock_source(config), LockSource.MANIFEST)

    def test_falls_back_to_deps_file_without_manifest_locks(self):
        config = MagicMock()
        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm="4.4",
            raw_normalized={},
            locks=None,
        )
        self.assertEqual(resolve_lock_source(config), LockSource.DEPS_FILE)


class DepsLockManagerManifestSourceTests(unittest.TestCase):
    def test_load_from_manifest_locks_git(self):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.policy.is_ci.return_value = False
        config.odoo_git_link = "https://github.com/odoo/odoo.git 17.0"
        config.dependencies = ["https://github.com/OCA/web.git 17.0"]
        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm="4.4",
            raw_normalized={},
            locks={
                "git": {
                    "https://github.com/odoo/odoo.git": "a" * 40,
                    "https://github.com/OCA/web.git": "b" * 40,
                }
            },
        )
        config.bootstrap.developing_project = None

        manager = DepsLockManager(config)
        lock = manager.load()

        self.assertEqual(manager.lock_source, LockSource.MANIFEST)
        self.assertIsNotNone(lock)
        assert lock is not None
        self.assertEqual(lock.platform.commit, "a" * 40)
        self.assertEqual(lock.dependencies[0].commit, "b" * 40)


if __name__ == "__main__":
    unittest.main()
