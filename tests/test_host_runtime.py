"""Unit tests for HostRuntimeState."""

import unittest

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
        from dev_project.config.state import DockerLayoutState

        config = Config.__new__(Config)
        runtime = HostRuntimeState(
            compose_service=ComposeOdooService(
                working_dir="/home/odoo",
                command=["/entrypoint"],
            ),
            container_run_mode=constants.RUN_MODE_BOOTSTRAP_ONLY,
            no_log_prefix=True,
            docker_compose_command="docker compose",
        )
        config._runtime = runtime
        config._docker = DockerLayoutState(docker_compose_command="docker-compose")

        self.assertIs(config.compose_service, runtime.compose_service)
        self.assertEqual(config.container_run_mode, constants.RUN_MODE_BOOTSTRAP_ONLY)
        self.assertTrue(config.no_log_prefix)
        self.assertEqual(config.docker_compose_command, "docker compose")

    def test_config_setters_update_runtime_state(self):
        from dev_project.config.config import Config
        from dev_project.config.state import DockerLayoutState

        instance = Config.__new__(Config)
        instance._runtime = HostRuntimeState()
        instance._docker = DockerLayoutState(docker_compose_command="docker-compose")

        instance.compose_service = None
        instance.container_run_mode = constants.RUN_MODE_BOOTSTRAP_ONLY
        instance.no_log_prefix = True
        instance.docker_compose_command = "docker compose"

        self.assertIsNone(instance.runtime.compose_service)
        self.assertEqual(
            instance.runtime.container_run_mode,
            constants.RUN_MODE_BOOTSTRAP_ONLY,
        )
        self.assertTrue(instance.runtime.no_log_prefix)
        self.assertEqual(instance.runtime.docker_compose_command, "docker compose")


if __name__ == "__main__":
    unittest.main()
