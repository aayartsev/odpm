"""Tests for deps.lock service_sources map."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.errors import PipelineError
from dev_project.git.deps_lock import (
    DepsLock,
    LockEntry,
    entry_for_service_source,
    load_deps_lock,
    save_deps_lock,
)
from dev_project.git.deps_lock_manager import DepsLockManager
from dev_project.manifest.reader import load_manifest
from dev_project.scenario_policy import ScenarioPolicy
from tests.test_manifest_v2_reader import _minimal_v2


class DepsLockServiceSourcesSchemaTests(unittest.TestCase):
    def test_roundtrip_service_sources_map(self):
        lock = DepsLock(
            generated_at="2026-07-14T12:00:00+00:00",
            platform=LockEntry(
                url="https://github.com/odoo/odoo",
                commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ),
            service_sources={
                "autoparts_env": LockEntry(
                    url="https://github.com/org/autoparts-env",
                    commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    branch="17.0",
                )
            },
        )
        with tempfile.TemporaryDirectory() as project_dir:
            path = os.path.join(project_dir, ".odpm", "deps.lock.json")
            save_deps_lock(path, lock)
            loaded = load_deps_lock(path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            entry = entry_for_service_source(loaded, "autoparts_env")
            self.assertIsNotNone(entry)
            assert entry is not None
            self.assertEqual(entry.commit, lock.service_sources["autoparts_env"].commit)

    def test_from_dict_without_service_sources_defaults_empty(self):
        lock = DepsLock.from_dict(
            {
                "schema_version": 1,
                "platform": {
                    "url": "https://github.com/odoo/odoo",
                    "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                },
                "dependencies": [],
            }
        )
        self.assertEqual(lock.service_sources, {})


class DepsLockManagerServiceSourcesTests(unittest.TestCase):
    def _config(self, project_dir: str, *, scenario: str = constants.CI_SCENARIO):
        view = load_manifest(
            _minimal_v2(
                service_sources={
                    "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
                },
            ),
        )
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = ScenarioPolicy.from_scenario(scenario)
        config.bootstrap.manifest_view = view
        config.bootstrap.service_source_paths = {
            "autoparts_env": os.path.join(project_dir, "service-sources", "autoparts_env"),
        }
        config.dependencies = []
        config.seed_dependency_urls = MagicMock(return_value=[])
        config.odoo_platform_project = MagicMock()
        config.dependencies_projects = []
        config.developing_project = MagicMock()
        config.handle_git_link = MagicMock(
            return_value=MagicMock(
                project_path=config.bootstrap.service_source_paths["autoparts_env"],
                branch="17.0",
                branch_explicit=True,
                commit_explicit=False,
                link_type=constants.GITLINK_TYPE_HTTP,
                is_true=True,
                resolve_head_sha=MagicMock(
                    return_value="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                ),
            )
        )
        return config

    def test_collect_writes_service_sources_entries(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            manager = DepsLockManager(config)
            with patch.object(
                manager,
                "_entry_from_project",
                return_value=LockEntry(
                    url="https://github.com/org/autoparts-env",
                    commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    branch="17.0",
                ),
            ), patch.object(
                manager,
                "_maybe_sync_manifest_git_locks",
            ):
                manager.collect_and_save()

            loaded = load_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"))
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertIn("autoparts_env", loaded.service_sources)

    def test_verify_service_sources_detects_drift_in_ci(self):
        with tempfile.TemporaryDirectory() as project_dir:
            lock = DepsLock(
                platform=LockEntry(
                    url="https://github.com/odoo/odoo",
                    commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                ),
                service_sources={
                    "autoparts_env": LockEntry(
                        url="https://github.com/org/autoparts-env",
                        commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    )
                },
            )
            save_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"), lock)
            config = self._config(project_dir, scenario=constants.CI_SCENARIO)
            config.handle_git_link.return_value.resolve_head_sha.return_value = (
                "cccccccccccccccccccccccccccccccccccccccc"
            )
            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()
            with self.assertRaises(PipelineError):
                manager.verify_service_sources()

    def test_lock_entries_for_service_sources_when_apply_mode(self):
        with tempfile.TemporaryDirectory() as project_dir:
            lock = DepsLock(
                platform=LockEntry(
                    url="https://github.com/odoo/odoo",
                    commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                ),
                service_sources={
                    "autoparts_env": LockEntry(
                        url="https://github.com/org/autoparts-env",
                        commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    )
                },
            )
            save_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"), lock)
            config = self._config(project_dir)
            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()
            entries = manager.lock_entries_for_service_sources()
            self.assertEqual(
                entries["autoparts_env"].commit,
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            )


if __name__ == "__main__":
    unittest.main()
