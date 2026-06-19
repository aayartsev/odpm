"""Tests for PostgreSQL admin role resolution and single-user bootstrap."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.database.postgres_admin import (
    admin_role_candidates,
    bootstrap_app_role_single_user,
    resolve_psql_admin_role,
    run_psql_as_admin,
)
from dev_project.errors import OdpmError


class AdminRoleCandidatesTests(unittest.TestCase):
    def test_prefers_app_role_then_legacy_postgres(self):
        self.assertEqual(admin_role_candidates(), ("odoo", "postgres"))


class ResolvePsqlAdminRoleTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.user_env.postgres_service_name = "db"
        return config

    @patch("dev_project.database.postgres_admin.psql_role_connects", side_effect=[False, True])
    def test_returns_first_working_candidate(self, _mock_connect):
        self.assertEqual(resolve_psql_admin_role(self._config()), "postgres")

    @patch("dev_project.database.postgres_admin.psql_role_connects", return_value=True)
    def test_returns_app_role_when_available(self, _mock_connect):
        self.assertEqual(resolve_psql_admin_role(self._config()), constants.POSTGRES_ODOO_USER)

    @patch("dev_project.database.postgres_admin.psql_role_connects", return_value=False)
    def test_returns_none_when_no_role_works(self, _mock_connect):
        self.assertIsNone(resolve_psql_admin_role(self._config()))


class RunPsqlAsAdminTests(unittest.TestCase):
    @patch("dev_project.database.postgres_admin.resolve_psql_admin_role", return_value="odoo")
    @patch("dev_project.database.postgres_admin._run_psql")
    def test_uses_resolved_admin_role(self, mock_run, _mock_resolve):
        config = MagicMock()
        mock_run.return_value = MagicMock(returncode=0, stdout="1", stderr="")
        result = run_psql_as_admin(config, "-tAc", "SELECT 1")
        self.assertEqual(result.returncode, 0)
        mock_run.assert_called_once_with(config, "odoo", "postgres", "-tAc", "SELECT 1", exec_user="postgres")

    @patch("dev_project.database.postgres_admin.resolve_psql_admin_role", return_value=None)
    def test_fails_when_admin_missing(self, _mock_resolve):
        config = MagicMock()
        config.user_env.postgres_service_name = "db"
        result = run_psql_as_admin(config, "-c", "SELECT 1")
        self.assertNotEqual(result.returncode, 0)


class BootstrapAppRoleSingleUserTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.user_env.postgres_service_name = "db"
        return config

    @patch("dev_project.database.postgres_admin._wait_for_postgres_ready")
    @patch("dev_project.database.postgres_admin.compose_up_service_detached")
    @patch("dev_project.database.postgres_admin.compose_run")
    @patch("dev_project.database.postgres_admin.compose_stop_service")
    def test_runs_single_user_recovery_flow(
        self, mock_stop, mock_run, mock_up, _mock_wait
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_up.return_value = MagicMock(returncode=0, stdout="", stderr="")
        bootstrap_app_role_single_user(self._config(), "CREATE ROLE odoo;")
        mock_stop.assert_called_once()
        mock_run.assert_called_once()
        mock_up.assert_called_once()
        self.assertEqual(mock_run.call_args.kwargs.get("entrypoint"), "postgres")
        run_args = mock_run.call_args.args
        self.assertIn("--single", run_args[2:])

    @patch("dev_project.database.postgres_admin.compose_up_service_detached")
    @patch("dev_project.database.postgres_admin.compose_run")
    @patch("dev_project.database.postgres_admin.compose_stop_service")
    def test_raises_when_single_user_fails(self, _mock_stop, mock_run, mock_up):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
        mock_up.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with self.assertRaises(OdpmError):
            bootstrap_app_role_single_user(self._config(), "CREATE ROLE odoo;")


class EnsureAppRoleAdminIntegrationTests(unittest.TestCase):
    @patch("dev_project.database.ensure_role.run_psql_as_admin")
    @patch("dev_project.database.ensure_role.wait_for_psql_admin_role")
    @patch("dev_project.database.ensure_role.bootstrap_app_role_single_user")
    @patch("dev_project.database.ensure_role.resolve_psql_admin_role", return_value=None)
    @patch("dev_project.database.ensure_role.probe_app_role_exists", return_value=False)
    @patch("dev_project.database.ensure_role.probe_postgres_ready", return_value=True)
    def test_bootstraps_when_no_admin_role(
        self,
        _mock_ready,
        _mock_role_exists,
        _mock_resolve,
        mock_bootstrap,
        _mock_wait,
        mock_psql,
    ):
        from dev_project.database.ensure_role import ensure_app_role

        mock_psql.return_value = MagicMock(returncode=0, stdout="", stderr="")
        config = MagicMock()
        config.user_env.postgres_service_name = "db"
        with patch(
            "dev_project.database.ensure_role.psql_role_connects", return_value=True
        ):
            result = ensure_app_role(config)
        mock_bootstrap.assert_called_once()
        mock_psql.assert_not_called()
        self.assertEqual(result.outcome, "created")


if __name__ == "__main__":
    unittest.main()
