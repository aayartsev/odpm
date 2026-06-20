"""Tests for PostgreSQL application role ensure logic."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dev_project.database.ensure_role import build_ensure_role_sql, ensure_app_role
from dev_project.errors import OdpmError


class BuildEnsureRoleSqlTests(unittest.TestCase):
    def test_sql_creates_role_when_missing(self):
        sql = build_ensure_role_sql("odoo", "odoo")
        self.assertIn("CREATE ROLE odoo", sql)
        self.assertIn("ALTER ROLE odoo", sql)
        self.assertIn("IF NOT EXISTS", sql)

    def test_single_user_sql_is_plain_create_role(self):
        from dev_project.database.ensure_role import build_single_user_bootstrap_sql

        sql = build_single_user_bootstrap_sql("odoo", "odoo")
        self.assertIn("CREATE ROLE odoo", sql)
        self.assertNotIn("DO $$", sql)

    def test_sql_escapes_single_quotes(self):
        sql = build_ensure_role_sql("o'doo", "p'ass")
        self.assertIn("o''doo", sql)
        self.assertIn("p''ass", sql)


class EnsureAppRoleTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.user_env.postgres_service_name = "db-dev"
        return config

    @patch("dev_project.database.ensure_role.psql_role_connects", return_value=False)
    @patch("dev_project.database.ensure_role.run_psql_as_admin")
    @patch("dev_project.database.ensure_role.resolve_psql_admin_role", return_value="odoo")
    @patch("dev_project.database.ensure_role.probe_app_role_exists")
    @patch("dev_project.database.ensure_role.probe_postgres_ready", return_value=True)
    def test_ensure_role_created_when_missing(
        self, _mock_ready, mock_role_exists, _mock_resolve, mock_psql, _mock_connects
    ):
        mock_role_exists.return_value = False
        mock_psql.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = ensure_app_role(self._config())
        self.assertEqual(result.outcome, "created")
        self.assertEqual(result.role, "odoo")
        mock_psql.assert_called_once()
        args = mock_psql.call_args.args
        self.assertIn("-c", args)

    @patch("dev_project.database.ensure_role.psql_role_connects", return_value=True)
    @patch("dev_project.database.ensure_role.run_psql_as_admin")
    @patch("dev_project.database.ensure_role.resolve_psql_admin_role", return_value="odoo")
    @patch("dev_project.database.ensure_role.probe_app_role_exists")
    @patch("dev_project.database.ensure_role.probe_postgres_ready", return_value=True)
    def test_ensure_role_updated_when_present(
        self, _mock_ready, mock_role_exists, _mock_resolve, mock_psql, _mock_connects
    ):
        mock_role_exists.return_value = True
        result = ensure_app_role(self._config())
        self.assertEqual(result.outcome, "updated")
        mock_psql.assert_not_called()

    @patch("dev_project.database.ensure_role.probe_postgres_ready", return_value=None)
    def test_ensure_role_fails_when_container_not_running(self, _mock_ready):
        with self.assertRaises(OdpmError):
            ensure_app_role(self._config())

    @patch("dev_project.database.ensure_role.probe_postgres_ready", return_value=False)
    def test_ensure_role_fails_when_postgres_not_ready(self, _mock_ready):
        with self.assertRaises(OdpmError):
            ensure_app_role(self._config())

    @patch("dev_project.database.ensure_role.psql_role_connects", return_value=False)
    @patch("dev_project.database.ensure_role.run_psql_as_admin")
    @patch("dev_project.database.ensure_role.resolve_psql_admin_role", return_value="odoo")
    @patch("dev_project.database.ensure_role.probe_app_role_exists", return_value=False)
    @patch("dev_project.database.ensure_role.probe_postgres_ready", return_value=True)
    def test_ensure_role_raises_on_psql_failure(
        self, _mock_ready, _mock_role_exists, _mock_resolve, mock_psql, _mock_connects
    ):
        mock_psql.return_value = MagicMock(
            returncode=1, stdout="", stderr="permission denied"
        )
        with self.assertRaises(OdpmError):
            ensure_app_role(self._config())


if __name__ == "__main__":
    unittest.main()
