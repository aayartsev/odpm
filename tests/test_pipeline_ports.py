"""Pipeline host ports contract tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from dev_project.config.state import CONFIG_PROPERTY_SHIMS
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.host.ports import (
    BootstrapHandle,
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

    def test_config_property_shims_inventory_non_empty(self):
        self.assertGreater(len(CONFIG_PROPERTY_SHIMS), 0)
        for slice_name, field_name, replacement in CONFIG_PROPERTY_SHIMS:
            self.assertTrue(slice_name)
            self.assertTrue(field_name)
            self.assertTrue(replacement)


if __name__ == "__main__":
    unittest.main()
