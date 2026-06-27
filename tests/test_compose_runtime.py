import unittest
from unittest.mock import ANY, MagicMock, patch

from dev_project.compose.runtime import (
    compose_cli_argv,
    compose_stack_is_healthy,
    compose_stack_services,
    container_is_running_and_healthy,
    should_force_recreate_compose,
)


class ContainerHealthTests(unittest.TestCase):
    def test_running_without_healthcheck_is_healthy(self):
        with patch("dev_project.compose.runtime._run_checked") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="true \n", stderr="")
            self.assertTrue(container_is_running_and_healthy("abc123"))

    def test_running_with_healthy_status(self):
        with patch("dev_project.compose.runtime._run_checked") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="true healthy\n", stderr="")
            self.assertTrue(container_is_running_and_healthy("abc123"))

    def test_unhealthy_container(self):
        with patch("dev_project.compose.runtime._run_checked") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="true unhealthy\n", stderr="")
            self.assertFalse(container_is_running_and_healthy("abc123"))

    def test_not_running_container(self):
        with patch("dev_project.compose.runtime._run_checked") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="false\n", stderr="")
            self.assertFalse(container_is_running_and_healthy("abc123"))


class ComposeStackHealthTests(unittest.TestCase):
    def _config(self, *, postgres_service_name: str = "db") -> MagicMock:
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.project_dir = "/tmp/project"
        config.user_env.postgres_service_name = postgres_service_name
        return config

    @patch("dev_project.compose.runtime.container_is_running_and_healthy", return_value=True)
    @patch("dev_project.compose.runtime._running_container_id_for_host")
    def test_compose_stack_is_healthy_uses_physical_odoo_service_name(
        self, mock_running_id, _mock_health
    ):
        config = self._config(postgres_service_name="acme-db")
        config.user_env.odoo_service_name = "acme-odoo"
        mock_running_id.side_effect = ["odoo-id", "db-id"]
        self.assertTrue(compose_stack_is_healthy(config))
        mock_running_id.assert_any_call(ANY, "acme-odoo")
        mock_running_id.assert_any_call(ANY, "acme-db")

    @patch("dev_project.compose.runtime.container_is_running_and_healthy", return_value=True)
    @patch("dev_project.compose.runtime._running_container_id_for_host")
    def test_compose_stack_is_healthy_uses_postgres_service_from_env(
        self, mock_running_id, _mock_health
    ):
        config = self._config(postgres_service_name="postgres")
        mock_running_id.side_effect = ["odoo-id", "postgres-id"]
        self.assertTrue(compose_stack_is_healthy(config))
        mock_running_id.assert_any_call(ANY, "postgres")

    @patch("dev_project.compose.runtime.container_is_running_and_healthy", return_value=True)
    @patch("dev_project.compose.runtime._running_container_id_for_host")
    def test_compose_stack_is_healthy_when_both_services_up(
        self, mock_running_id, _mock_health
    ):
        mock_running_id.side_effect = ["odoo-id", "db-id"]
        self.assertTrue(compose_stack_is_healthy(self._config()))

    @patch("dev_project.compose.runtime.container_is_running_and_healthy")
    @patch("dev_project.compose.runtime._running_container_id_for_host")
    def test_compose_stack_unhealthy_when_odoo_unhealthy(
        self, mock_running_id, mock_health
    ):
        mock_running_id.side_effect = ["odoo-id", "db-id"]
        mock_health.side_effect = [False, True]
        self.assertFalse(compose_stack_is_healthy(self._config()))

    @patch("dev_project.compose.runtime._running_container_id_for_host", return_value=None)
    def test_compose_stack_unhealthy_when_service_missing(self, _mock_running_id):
        self.assertFalse(compose_stack_is_healthy(self._config()))

    @patch(
        "dev_project.compose.runtime.compose_stack_is_healthy_for_host",
        return_value=True,
    )
    def test_should_not_force_recreate_when_healthy(self, _mock_stack):
        self.assertFalse(should_force_recreate_compose(self._config()))

    @patch(
        "dev_project.compose.runtime.compose_stack_is_healthy_for_host",
        return_value=False,
    )
    def test_should_force_recreate_when_unhealthy(self, _mock_stack):
        self.assertTrue(should_force_recreate_compose(self._config()))


class ComposeCliArgvTests(unittest.TestCase):
    def test_compose_stack_services_uses_physical_names(self):
        config = MagicMock()
        config.user_env.odoo_service_name = "acme-odoo"
        config.user_env.postgres_service_name = "acme-db"
        self.assertEqual(compose_stack_services(config), ("acme-odoo", "acme-db"))

    def test_compose_cli_argv_includes_project_when_prefix_set(self):
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.user_env.compose_project_name = "acme"
        with patch(
            "dev_project.host.context.HostProjectContext.from_config",
            return_value=MagicMock(
                docker_compose_command="docker compose",
                user_env=config.user_env,
            ),
        ):
            self.assertEqual(
                compose_cli_argv(config),
                ["docker", "compose", "-p", "acme"],
            )

    @patch("dev_project.compose.runtime._run_checked")
    def test_running_container_id_passes_project_flag(self, mock_run):
        from dev_project.compose.runtime import compose_service_container_id

        mock_run.return_value = MagicMock(returncode=0, stdout="cid\n", stderr="")
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.project_dir = "/tmp/project"
        config.user_env.compose_project_name = "acme"
        config.user_env.postgres_service_name = "acme-db"
        with patch(
            "dev_project.host.context.HostProjectContext.from_config",
            return_value=MagicMock(
                docker_compose_command="docker compose",
                project_dir="/tmp/project",
                user_env=config.user_env,
            ),
        ):
            compose_service_container_id(config, "acme-db")
        self.assertEqual(
            mock_run.call_args.args[0],
            ["docker", "compose", "-p", "acme", "ps", "-q", "acme-db"],
        )


if __name__ == "__main__":
    unittest.main()
