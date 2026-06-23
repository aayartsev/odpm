"""Pipeline host ports contract tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from dev_project.config.state import BOOTSTRAP_HANDLE_SURFACES, CONFIG_PROPERTY_SHIMS
from dev_project.host.ports import BootstrapHandle
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.host.ports import (
    ComposePorts,
    PipelinePorts,
    PlanPorts,
    RuntimePorts,
    ports_from_config,
)
from dev_project.project_env import CreateProjectEnvironment


class PipelinePortsTests(unittest.TestCase):
    def test_from_setup_builds_shared_bootstrap_and_host_ctx(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs()
        config.user_env = MagicMock()
        project_env = CreateProjectEnvironment(config)

        ports = PipelinePorts.from_setup(config, project_env, OdpmCliArgs())

        self.assertIsInstance(ports.plan, PlanPorts)
        self.assertIsInstance(ports.compose, ComposePorts)
        self.assertIsInstance(ports.runtime, RuntimePorts)
        self.assertIs(ports.plan.bootstrap, ports.compose.bootstrap)
        self.assertIs(ports.plan.bootstrap, ports.runtime.bootstrap)
        self.assertIs(ports.bootstrap.config, config)
        self.assertIs(ports.compose.project_env, project_env)
        self.assertIs(ports.runtime.project_env, project_env)
        self.assertIsInstance(ports.plan.host_ctx, HostProjectContext)

    def test_ports_from_config_without_project_env(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs()
        config.user_env = MagicMock()

        ports = ports_from_config(config)

        self.assertIsInstance(ports, PipelinePorts)
        self.assertIsInstance(ports.compose.project_env, CreateProjectEnvironment)

    def test_bootstrap_handle_exposes_manifest_read_model(self):
        from dev_project.manifest.reader import ManifestView

        config = MagicMock()
        view = ManifestView(
            manifest_schema=2,
            requires_odpm=">=4.5.0",
            services=None,
            hooks=None,
            locks=None,
            raw_normalized={},
            source_raw={},
        )
        config.bootstrap.manifest_view = view
        config.bootstrap.repo_odpm_json = "/tmp/project/odpm.json"

        bootstrap = BootstrapHandle(config=config)

        self.assertIs(bootstrap.manifest_view, view)
        self.assertEqual(bootstrap.repo_odpm_json, "/tmp/project/odpm.json")

    def test_bootstrap_handle_exposes_narrow_git_and_lock_surfaces(self):
        config = MagicMock()
        config._git_repos = MagicMock(name="git_repos")
        config.compute_venv_lock_hash.return_value = "abc123"

        bootstrap = BootstrapHandle(config=config)

        self.assertIs(bootstrap.git_repos, config._git_repos)
        self.assertEqual(bootstrap.compute_venv_lock_hash(), "abc123")
        lock_manager = bootstrap.new_lock_manager()
        from dev_project.git.deps_lock_manager import DepsLockManager

        self.assertIsInstance(lock_manager, DepsLockManager)

    def test_bootstrap_handle_surfaces_inventory(self):
        self.assertEqual(
            BOOTSTRAP_HANDLE_SURFACES,
            ("config", "git_repos", "new_lock_manager", "compute_venv_lock_hash"),
        )

    def test_repo_odpm_json_shim_is_not_duplicated(self):
        repo_shims = [
            replacement
            for _slice, field, replacement in CONFIG_PROPERTY_SHIMS
            if field == "repo_odpm_json"
        ]
        self.assertEqual(repo_shims, ["host_ctx.repo_odpm_json"])

    def test_manifest_view_shim_points_at_host_ctx(self):
        shims = dict(
            (field, replacement)
            for _slice, field, replacement in CONFIG_PROPERTY_SHIMS
            if field == "manifest_view"
        )
        self.assertEqual(shims["manifest_view"], "host_ctx.manifest_view")

    def test_config_property_shims_inventory_non_empty(self):
        self.assertGreater(len(CONFIG_PROPERTY_SHIMS), 0)
        for slice_name, field_name, replacement in CONFIG_PROPERTY_SHIMS:
            self.assertTrue(slice_name)
            self.assertTrue(field_name)
            self.assertTrue(replacement)


if __name__ == "__main__":
    unittest.main()
