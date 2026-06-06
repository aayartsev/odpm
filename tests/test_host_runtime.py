"""Unit tests for HostRuntimeState."""

import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.host_runtime import HostRuntimeState
from dev_project.start_command import ComposeOdooService


class HostRuntimeStateTests(unittest.TestCase):
    def test_resolved_docker_compose_command_prefers_runtime_override(self):
        runtime = HostRuntimeState(docker_compose_command="docker compose")
        self.assertEqual(
            runtime.resolved_docker_compose_command("docker-compose"),
            "docker compose",
        )

    def test_resolved_docker_compose_command_falls_back_to_layout_default(self):
        runtime = HostRuntimeState()
        self.assertEqual(
            runtime.resolved_docker_compose_command("docker-compose"),
            "docker-compose",
        )

    def test_config_runtime_properties_delegate(self):
        from dev_project.config.config import Config

        config = MagicMock(spec=Config)
        runtime = HostRuntimeState(
            compose_service=ComposeOdooService(
                working_dir="/home/odoo",
                command=["/entrypoint"],
            ),
            container_run_mode=constants.RUN_MODE_BOOTSTRAP_ONLY,
            no_log_prefix=True,
            docker_compose_command="docker compose",
        )
        config.runtime = runtime
        config._docker = MagicMock(docker_compose_command="docker-compose")

        compose_service_getter = Config.compose_service.fget
        container_run_mode_getter = Config.container_run_mode.fget
        no_log_prefix_getter = Config.no_log_prefix.fget
        docker_compose_command_getter = Config.docker_compose_command.fget

        self.assertIs(compose_service_getter(config), runtime.compose_service)
        self.assertEqual(
            container_run_mode_getter(config),
            constants.RUN_MODE_BOOTSTRAP_ONLY,
        )
        self.assertTrue(no_log_prefix_getter(config))
        self.assertEqual(docker_compose_command_getter(config), "docker compose")

    def test_config_setters_update_runtime_state(self):
        from dev_project.config.config import Config

        instance = MagicMock()
        instance.runtime = HostRuntimeState()
        instance._docker = MagicMock(docker_compose_command="docker-compose")

        Config.compose_service.fset(instance, None)
        Config.container_run_mode.fset(instance, constants.RUN_MODE_BOOTSTRAP_ONLY)
        Config.no_log_prefix.fset(instance, True)
        Config.docker_compose_command.fset(instance, "docker compose")

        self.assertIsNone(instance.runtime.compose_service)
        self.assertEqual(
            instance.runtime.container_run_mode,
            constants.RUN_MODE_BOOTSTRAP_ONLY,
        )
        self.assertTrue(instance.runtime.no_log_prefix)
        self.assertEqual(instance.runtime.docker_compose_command, "docker compose")


if __name__ == "__main__":
    unittest.main()
