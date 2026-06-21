"""Tests for git lock source plan warnings."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.git.deps_lock import DepsLock, LockEntry, save_deps_lock
from dev_project.manifest.reader import ManifestView
from dev_project.plan.locks_preview import collect_git_lock_warnings


class GitLockPlanWarningsTests(unittest.TestCase):
    def test_manifest_source_warning(self):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm="4.4",
            raw_normalized={},
            locks={"git": {"https://github.com/odoo/odoo.git": "a" * 40}},
        )
        warnings = collect_git_lock_warnings(config)
        self.assertTrue(
            any("manifest locks.git" in warning for warning in warnings)
        )

    def test_divergence_warning_when_both_sources_present(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.project_dir = tmp
            config.bootstrap.manifest_view = ManifestView(
                manifest_schema=constants.MANIFEST_SCHEMA_V2,
                requires_odpm="4.4",
                raw_normalized={},
                locks={"git": {"https://github.com/odoo/odoo.git": "a" * 40}},
            )
            save_deps_lock(
                f"{tmp}/.odpm/deps.lock.json",
                DepsLock(
                    platform=LockEntry(
                        url="https://github.com/odoo/odoo.git",
                        commit="b" * 40,
                    )
                ),
            )
            warnings = collect_git_lock_warnings(config)
            self.assertTrue(
                any("manifest locks.git vs deps.lock.json differ" in warning
                    for warning in warnings)
            )
            self.assertTrue(
                any("Canonical git pins" in warning for warning in warnings)
            )


if __name__ == "__main__":
    unittest.main()
