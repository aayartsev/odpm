import unittest
from unittest.mock import MagicMock

from dev_project.inside_docker_app.odoo_checker.sql_runner import OdooSqlRunner


class OdooSqlRunnerTests(unittest.TestCase):
    def test_execute_queries_runs_each_statement(self):
        odoo = MagicMock()
        cursor = MagicMock()
        odoo.sql_db.db_connect.return_value.cursor.return_value = cursor
        runner = OdooSqlRunner(odoo)

        runner.execute_queries("demo", ["SELECT 1", "SELECT 2"])

        self.assertEqual(cursor.execute.call_count, 2)
        self.assertEqual(cursor.commit.call_count, 2)

    def test_execute_queries_logs_and_continues_on_failure(self):
        odoo = MagicMock()
        cursor = MagicMock()
        cursor.execute.side_effect = [RuntimeError("boom"), None]
        odoo.sql_db.db_connect.return_value.cursor.return_value = cursor
        runner = OdooSqlRunner(odoo)

        runner.execute_queries("demo", ["BAD", "OK"])

        self.assertEqual(cursor.execute.call_count, 2)
        cursor.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
