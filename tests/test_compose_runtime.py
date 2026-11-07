import unittest
from unittest.mock import MagicMock, patch

from dev_project.compose.runtime import (
    compose_cli_argv,
    compose_stack_is_healthy,
    compose_stack_services,
    container_is_running_and_healthy,
    should_force_recreate_compose,
)
from dev_project.compose.runtime import compose_service_container_id


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
    def _host_ctx(self, *, postgres_service_name: str = "db") -> MagicMock:
        host_ctx = MagicMock()
        host_ctx.docker_compose_command = "docker compose"
        host_ctx.project_dir = "/tmp/project"
        host_ctx.user_env.postgres_service_name = postgres_service_name
        host_ctx.user_env.odoo_service_name = "odoo"
        return host_ctx

    @patch("dev_project.compose.runtime.container_is_running_and_healthy", return_value=True)
    @patch("dev_project.compose.runtime.compose_service_container_id")
    def test_compose_stack_is_healthy_uses_physical_odoo_service_name(
        self, mock_running_id, _mock_health
    ):
        host_ctx = self._host_ctx(postgres_service_name="acme-db")
        host_ctx.user_env.odoo_service_name = "acme-odoo"
        mock_running_id.side_effect = ["odoo-id", "db-id"]
        self.assertTrue(compose_stack_is_healthy(host_ctx))
        mock_running_id.assert_any_call(host_ctx, "acme-odoo")
        mock_running_id.assert_any_call(host_ctx, "acme-db")

    @patch("dev_project.compose.runtime.container_is_running_and_healthy", return_value=True)
    @patch("dev_project.compose.runtime.compose_service_container_id")
    def test_compose_stack_is_healthy_uses_postgres_service_from_env(
        self, mock_running_id, _mock_health
    ):
        host_ctx = self._host_ctx(postgres_service_name="postgres")
        mock_running_id.side_effect = ["odoo-id", "postgres-id"]
        self.assertTrue(compose_stack_is_healthy(host_ctx))
        mock_running_id.assert_any_call(host_ctx, "postgres")

    @patch("dev_project.compose.runtime.container_is_running_and_healthy", return_value=True)
    @patch("dev_project.compose.runtime.compose_service_container_id")
    def test_compose_stack_is_healthy_when_both_services_up(
        self, mock_running_id, _mock_health
    ):
        mock_running_id.side_effect = ["odoo-id", "db-id"]
        self.assertTrue(compose_stack_is_healthy(self._host_ctx()))

    @patch("dev_project.compose.runtime.container_is_running_and_healthy")
    @patch("dev_project.compose.runtime.compose_service_container_id")
    def test_compose_stack_unhealthy_when_odoo_unhealthy(
        self, mock_running_id, mock_health
    ):
        mock_running_id.side_effect = ["odoo-id", "db-id"]
        mock_health.side_effect = [False, True]
        self.assertFalse(compose_stack_is_healthy(self._host_ctx()))

    @patch("dev_project.compose.runtime.compose_service_container_id", return_value=None)
    def test_compose_stack_unhealthy_when_service_missing(self, _mock_running_id):
        self.assertFalse(compose_stack_is_healthy(self._host_ctx()))

    @patch(
        "dev_project.compose.runtime.compose_stack_is_healthy",
        return_value=True,
    )
    def test_should_not_force_recreate_when_healthy(self, _mock_stack):
        self.assertFalse(should_force_recreate_compose(self._host_ctx()))

    @patch(
        "dev_project.compose.runtime.compose_stack_is_healthy",
        return_value=False,
    )
    def test_should_force_recreate_when_unhealthy(self, _mock_stack):
        self.assertTrue(should_force_recreate_compose(self._host_ctx()))


class ComposeCliArgvTests(unittest.TestCase):
    def test_compose_stack_services_uses_physical_names(self):
        host_ctx = MagicMock()
        host_ctx.user_env.odoo_service_name = "acme-odoo"
        host_ctx.user_env.postgres_service_name = "acme-db"
        self.assertEqual(compose_stack_services(host_ctx), ("acme-odoo", "acme-db"))

    def test_compose_cli_argv_includes_project_when_prefix_set(self):
        host_ctx = MagicMock()
        host_ctx.docker_compose_command = "docker compose"
        host_ctx.user_env.compose_project_name = "acme"
        self.assertEqual(
            compose_cli_argv(host_ctx),
            ["docker", "compose", "-p", "acme"],
        )

    def test_compose_cli_argv_includes_project_when_suffix_set(self):
        host_ctx = MagicMock()
        host_ctx.docker_compose_command = "docker compose"
        host_ctx.user_env.compose_project_name = "dev"
        self.assertEqual(
            compose_cli_argv(host_ctx),
            ["docker", "compose", "-p", "dev"],
        )

    def test_compose_cli_argv_includes_project_when_prefix_and_suffix_set(self):
        host_ctx = MagicMock()
        host_ctx.docker_compose_command = "docker compose"
        host_ctx.user_env.compose_project_name = "acme-dev"
        self.assertEqual(
            compose_cli_argv(host_ctx),
            ["docker", "compose", "-p", "acme-dev"],
        )

    @patch("dev_project.compose.runtime._run_checked")
    def test_running_container_id_passes_project_flag(self, mock_run):

        mock_run.return_value = MagicMock(returncode=0, stdout="cid\n", stderr="")
        host_ctx = MagicMock()
        host_ctx.docker_compose_command = "docker compose"
        host_ctx.project_dir = "/tmp/project"
        host_ctx.user_env.compose_project_name = "acme"
        host_ctx.user_env.postgres_service_name = "acme-db"
        compose_service_container_id(host_ctx, "acme-db")
        self.assertEqual(
            mock_run.call_args.args[0],
            ["docker", "compose", "-p", "acme", "ps", "-q", "acme-db"],
        )


if __name__ == "__main__":
    unittest.main()
