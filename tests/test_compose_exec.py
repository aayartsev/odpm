"""Tests for docker compose exec helpers."""

from __future__ import annotations

from dev_project.host.ports import BootstrapHandle

import unittest
from unittest.mock import MagicMock, patch

from dev_project.database.compose_exec import (
    compose_up_detached_argv,
    compose_up_service_detached,
)
from dev_project.compose.runtime import compose_cli_argv
from dev_project.docker_capabilities import DockerCapabilities
from dev_project.host.runtime import HostRuntimeState


def _capabilities(*, supports_compose_up_yes: bool) -> DockerCapabilities:
    return DockerCapabilities(
        compose_command="docker compose",
        compose_version_text="Docker Compose version v2.24.0",
        supports_no_log_prefix=True,
        supports_compose_up_yes=supports_compose_up_yes,
        supports_pull_policy_never=True,
    )


class ComposeUpServiceDetachedTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.runtime = HostRuntimeState()
        config.runtime.docker_compose_command = "docker compose"
        config.user_env.compose_project_name = None
        return config

    def test_compose_cli_argv_includes_project_when_prefix_set(self):
        host_ctx = MagicMock()
        host_ctx.docker_compose_command = "docker compose"
        host_ctx.user_env.compose_project_name = "acme"
        self.assertEqual(
            compose_cli_argv(host_ctx),
            ["docker", "compose", "-p", "acme"],
        )

    def test_argv_includes_yes_when_compose_supports_it(self):
        config = self._config()
        config.runtime.docker_capabilities = _capabilities(supports_compose_up_yes=True)
        self.assertEqual(
            compose_up_detached_argv(BootstrapHandle(_assembled=config), "db-dev"),
            ["docker", "compose", "up", "-d", "-y", "db-dev"],
        )

    def test_argv_omits_yes_on_legacy_compose(self):
        config = self._config()
        config.runtime.docker_capabilities = _capabilities(supports_compose_up_yes=False)
        self.assertEqual(
            compose_up_detached_argv(BootstrapHandle(_assembled=config), "db-dev"),
            ["docker", "compose", "up", "-d", "db-dev"],
        )

    def test_argv_includes_project_and_yes_when_prefix_active(self):
        config = self._config()
        config.user_env.compose_project_name = "acme"
        config.runtime.docker_capabilities = _capabilities(supports_compose_up_yes=True)
        bootstrap = BootstrapHandle(_assembled=config)
        with patch.object(
            bootstrap,
            "host_context",
            return_value=MagicMock(
                docker_compose_command="docker compose",
                user_env=config.user_env,
            ),
        ):
            self.assertEqual(
                compose_up_detached_argv(bootstrap, "acme-db"),
                ["docker", "compose", "-p", "acme", "up", "-d", "-y", "acme-db"],
            )

    @patch("dev_project.database.compose_exec.run_checked")
    def test_compose_up_service_detached_delegates_to_run_checked(
        self, mock_run: MagicMock
    ) -> None:
        config = self._config()
        config.runtime.docker_capabilities = _capabilities(supports_compose_up_yes=True)
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        compose_up_service_detached(BootstrapHandle(_assembled=config), "db-dev")

        mock_run.assert_called_once()
        self.assertEqual(
            mock_run.call_args.args[0],
            ["docker", "compose", "up", "-d", "-y", "db-dev"],
        )
        self.assertEqual(mock_run.call_args.kwargs["cwd"], "/tmp/project")


if __name__ == "__main__":
    unittest.main()
