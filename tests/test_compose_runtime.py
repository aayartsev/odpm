import unittest
from unittest.mock import ANY, MagicMock, patch

from dev_project.compose.runtime import (
    compose_stack_is_healthy,
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


if __name__ == "__main__":
    unittest.main()
