"""Tests for checker PostgreSQL wait and credential verification."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from dev_project.inside_docker_app.odoo_checker.dispatch import wait_for_postgres

from tests.container_config_helpers import minimal_container_config


class WaitForPostgresTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        return minimal_container_config(
            odoo_config_data={
                "options": {
                    "db_host": "db-dev",
                    "db_port": "5432",
                    "db_user": "odoo",
                    "db_password": "odoo",
                }
            }
        )

    @patch("dev_project.inside_docker_app.odoo_checker.dispatch.record_last_run_from_container")
    @patch("dev_project.inside_docker_app.odoo_checker.dispatch.PostgresWaiter")
    def test_always_verifies_credentials_and_records_last_run(
        self, waiter_cls, record_last_run
    ):
        waiter = MagicMock()
        waiter_cls.return_value = waiter
        config = self._config()
        record_last_run.return_value = "/run/odpm/database/last_run.json"

        wait_for_postgres(config)

        waiter.wait_for_postgres.assert_called_once_with()
        waiter.verify_postgres_credentials.assert_called_once_with(
            dbname="postgres",
            user="odoo",
            password="odoo",
        )
        record_last_run.assert_called_once_with(config)

    @patch("dev_project.inside_docker_app.odoo_checker.dispatch.record_last_run_from_container")
    @patch("dev_project.inside_docker_app.odoo_checker.dispatch.PostgresWaiter")
    def test_also_verifies_named_database_when_db_name_set(
        self, waiter_cls, record_last_run
    ):
        waiter = MagicMock()
        waiter_cls.return_value = waiter
        config = self._config()
        record_last_run.return_value = "/run/odpm/database/last_run.json"

        wait_for_postgres(config, db_name="mydb")

        self.assertEqual(
            waiter.verify_postgres_credentials.call_args_list,
            [
                call(dbname="postgres", user="odoo", password="odoo"),
                call(
                    dbname="mydb",
                    user="odoo",
                    password="odoo",
                    allow_missing=True,
                ),
            ],
        )
        record_last_run.assert_called_once_with(config)


if __name__ == "__main__":
    unittest.main()
