"""Unit tests for PostgresWaiter credential verification helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dev_project.inside_docker_app.exceptions import PostgresError
from dev_project.inside_docker_app.odoo_checker import postgres_waiter as waiter_mod
from dev_project.inside_docker_app.odoo_checker.postgres_waiter import (
    PostgresWaiter,
    _is_missing_database_error,
    _is_transient_operational_error,
)


class TransientAndMissingHelpersTests(unittest.TestCase):
    def test_recovery_is_transient(self):
        exc = Exception("FATAL:  the database system is in recovery mode")
        self.assertTrue(_is_transient_operational_error(exc))

    def test_not_yet_accepting_is_transient(self):
        exc = Exception(
            "FATAL:  the database system is not yet accepting connections"
        )
        self.assertTrue(_is_transient_operational_error(exc))

    def test_missing_database_detected(self):
        exc = Exception('FATAL:  database "mydb" does not exist')
        self.assertTrue(_is_missing_database_error(exc))

    def test_role_missing_is_not_missing_database(self):
        exc = Exception('FATAL:  role "odoo" does not exist')
        self.assertFalse(_is_missing_database_error(exc))


class VerifyPostgresCredentialsTests(unittest.TestCase):
    def _waiter(self) -> PostgresWaiter:
        return PostgresWaiter(host="db", port=5432, timeout=5, check_interval=0.01)

    def _op_error_type(self):
        return type("OperationalError", (Exception,), {})

    @patch.object(waiter_mod, "time")
    def test_retries_recovery_then_succeeds(self, mock_time):
        clock = {"t": 0.0}

        def _now():
            clock["t"] += 0.1
            return clock["t"]

        mock_time.time.side_effect = _now
        mock_time.sleep = MagicMock()
        waiter = self._waiter()
        op_err = self._op_error_type()
        recovery = op_err("the database system is in recovery mode")
        good_conn = MagicMock()
        cur = MagicMock()
        good_conn.cursor.return_value.__enter__.return_value = cur
        good_conn.cursor.return_value.__exit__.return_value = False

        fake_psycopg2 = MagicMock()
        fake_psycopg2.OperationalError = op_err
        fake_psycopg2.connect.side_effect = [recovery, good_conn]

        with patch.dict("sys.modules", {"psycopg2": fake_psycopg2}):
            waiter.verify_postgres_credentials("mydb", "odoo", "odoo")

        self.assertEqual(fake_psycopg2.connect.call_count, 2)

    @patch.object(waiter_mod, "time")
    def test_allow_missing_returns_on_missing_database(self, mock_time):
        mock_time.time.return_value = 0.0
        waiter = self._waiter()
        op_err = self._op_error_type()
        missing = op_err('database "mydb" does not exist')
        fake_psycopg2 = MagicMock()
        fake_psycopg2.OperationalError = op_err
        fake_psycopg2.connect.side_effect = missing

        with patch.dict("sys.modules", {"psycopg2": fake_psycopg2}):
            waiter.verify_postgres_credentials(
                "mydb", "odoo", "odoo", allow_missing=True
            )

    @patch.object(waiter_mod, "time")
    def test_missing_database_raises_without_allow_missing(self, mock_time):
        mock_time.time.return_value = 0.0
        waiter = self._waiter()
        op_err = self._op_error_type()
        missing = op_err('database "mydb" does not exist')
        fake_psycopg2 = MagicMock()
        fake_psycopg2.OperationalError = op_err
        fake_psycopg2.connect.side_effect = missing

        with patch.dict("sys.modules", {"psycopg2": fake_psycopg2}):
            with self.assertRaises(PostgresError):
                waiter.verify_postgres_credentials("mydb", "odoo", "odoo")

    @patch.object(waiter_mod, "time")
    def test_role_missing_raises_even_with_allow_missing(self, mock_time):
        mock_time.time.return_value = 0.0
        waiter = self._waiter()
        op_err = self._op_error_type()
        role_err = op_err('role "odoo" does not exist')
        fake_psycopg2 = MagicMock()
        fake_psycopg2.OperationalError = op_err
        fake_psycopg2.connect.side_effect = role_err

        with patch.dict("sys.modules", {"psycopg2": fake_psycopg2}):
            with self.assertRaises(PostgresError):
                waiter.verify_postgres_credentials(
                    "mydb", "odoo", "odoo", allow_missing=True
                )


if __name__ == "__main__":
    unittest.main()
