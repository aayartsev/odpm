"""Tests for POSTGRES_SERVICE_NAME parsing."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project import constants
from dev_project.host.postgres_service_name import parse_postgres_service_name
from dev_project.host.user_env import CreateUserEnvironment
from tests.test_noninteractive_init import _make_pd_manager


class PostgresServiceNameParsingTests(unittest.TestCase):
    def test_default_when_missing_or_blank(self):
        self.assertEqual(
            parse_postgres_service_name(None),
            constants.DEFAULT_POSTGRES_SERVICE_NAME,
        )
        self.assertEqual(parse_postgres_service_name(""), "db")
        self.assertEqual(parse_postgres_service_name("   "), "db")

    def test_accepts_valid_names(self):
        self.assertEqual(parse_postgres_service_name("postgres"), "postgres")
        self.assertEqual(parse_postgres_service_name("db_main"), "db_main")
        self.assertEqual(parse_postgres_service_name("pg-19"), "pg-19")

    def test_rejects_invalid_names(self):
        self.assertEqual(parse_postgres_service_name("DB"), "db")
        self.assertEqual(parse_postgres_service_name("db.example"), "db")
        self.assertEqual(parse_postgres_service_name("1db"), "db")


class PostgresServiceNameUserEnvTests(unittest.TestCase):
    @patch("dev_project.host.user_env._stdin_is_interactive", return_value=False)
    def test_reads_postgres_service_name_from_project_env(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = Path(project_dir) / ".env"
            project_env.write_text(
                "\n".join(
                    [
                        "BACKUP_DIR=/tmp/backups",
                        "ODOO_PROJECTS_DIR=/tmp/projects",
                        "PATH_TO_SSH_KEY=",
                        "ODOO_PORT=8069",
                        "POSTGRES_PORT=5432",
                        "POSTGRES_SERVICE_NAME=postgres",
                        "DEBUGGER_PORT=5678",
                        "GEVENT_PORT=8072",
                        "ODPM_SCENARIO=developer",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
                user_env = CreateUserEnvironment(pd_manager)
            self.assertEqual(user_env.postgres_service_name, "postgres")


if __name__ == "__main__":
    unittest.main()
