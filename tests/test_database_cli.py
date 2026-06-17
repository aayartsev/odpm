"""Tests for odpm database CLI subcommands."""

from __future__ import annotations

import json
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import dev_project.host.cli.parse_args as parse_args_module
from dev_project.database.schema import (
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseCurrentState,
    DatabaseOdooConfFingerprint,
)
from dev_project.database.status import DatabaseStatusReport, collect_database_status
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.plan.cli import is_database_mode


def _static_state() -> DatabaseCurrentState:
    return DatabaseCurrentState(
        odpm_scenario="developer",
        engine="postgres",
        compose=DatabaseComposeFingerprint(
            service_name="db-dev",
            image_tag="17",
            data_path_abs="/tmp/pg",
            host_port=5432,
        ),
        odoo_conf=DatabaseOdooConfFingerprint(
            db_host="db-dev",
            db_port=5432,
            db_user="odoo",
        ),
        cluster=DatabaseClusterFingerprint(
            data_dir_nonempty=True,
            pg_major=17,
            app_role="odoo",
            app_role_present=False,
        ),
    )


class DatabaseCliArgsTests(unittest.TestCase):
    def test_parse_database_status(self):
        cli_args = parse_cli_args(["database", "status"])
        self.assertEqual(cli_args.command, "database")
        self.assertEqual(cli_args.database_subcommand, "status")
        self.assertEqual(cli_args.database_status_format, "table")
        self.assertTrue(is_database_mode(cli_args))

    def test_parse_database_status_json(self):
        cli_args = parse_cli_args(["database", "status", "--format", "json"])
        self.assertEqual(cli_args.database_status_format, "json")

    def test_parse_database_ensure_role(self):
        cli_args = parse_cli_args(["database", "ensure-role"])
        self.assertEqual(cli_args.database_subcommand, "ensure-role")


class DatabaseStatusCollectTests(unittest.TestCase):
    @patch("dev_project.database.status.probe_app_role_exists", return_value=False)
    @patch("dev_project.database.status.probe_postgres_ready", return_value=True)
    @patch(
        "dev_project.database.status.probe_postgres_container_running",
        return_value=True,
    )
    @patch("dev_project.database.status.collect_database_state")
    @patch("dev_project.database.status.load_last_run", return_value=None)
    def test_collect_status_sets_app_role_present_and_drift(
        self,
        _mock_last_run,
        mock_collect,
        _mock_running,
        _mock_ready,
        _mock_role,
    ):
        mock_collect.return_value = DatabaseCurrentState(
            odpm_scenario="developer",
            engine="postgres",
            compose=DatabaseComposeFingerprint(
                service_name="db-dev",
                image_tag="17",
                data_path_abs="/tmp/pg",
                host_port=5432,
            ),
            odoo_conf=DatabaseOdooConfFingerprint(
                db_host="db-dev",
                db_port=5432,
                db_user="odoo",
            ),
            cluster=DatabaseClusterFingerprint(
                data_dir_nonempty=True,
                pg_major=17,
                app_role="odoo",
                app_role_present=None,
            ),
        )
        report = collect_database_status(MagicMock())
        self.assertFalse(report.app_role_present)
        kinds = {drift.kind for drift in report.drifts}
        self.assertIn("app_role_missing", kinds)
        self.assertIn("first_run", kinds)


class DatabaseCommandHandlerTests(unittest.TestCase):
    @patch("dev_project.database.commands.collect_database_status")
    def test_status_table_logs_report(self, mock_collect):
        from dev_project.database.commands import run_database_command

        mock_collect.return_value = DatabaseStatusReport(
            current=_static_state(),
            last_run=None,
            drifts=(),
            postgres_container_running=True,
            postgres_ready=True,
            app_role_present=False,
        )
        config = MagicMock()
        with patch("dev_project.database.commands._logger") as mock_logger:
            code = run_database_command(
                OdpmCliArgs(
                    command="database",
                    database_subcommand="status",
                ),
                config,
            )
        self.assertEqual(code, 0)
        mock_logger.info.assert_called_once()

    @patch("dev_project.database.commands.collect_database_status")
    def test_status_json_prints_payload(self, mock_collect):
        from dev_project.database.commands import run_database_command

        mock_collect.return_value = DatabaseStatusReport(
            current=_static_state(),
            last_run=None,
            drifts=(),
            postgres_container_running=True,
            postgres_ready=True,
            app_role_present=False,
        )
        config = MagicMock()
        buffer = StringIO()
        with patch("sys.stdout", buffer):
            code = run_database_command(
                OdpmCliArgs(
                    command="database",
                    database_subcommand="status",
                    database_status_format="json",
                ),
                config,
            )
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["compose"]["service_name"], "db-dev")
        self.assertFalse(payload["app_role_present"])

    @patch("dev_project.database.commands.ensure_app_role")
    def test_ensure_role_command(self, mock_ensure):
        from dev_project.database.commands import run_database_command
        from dev_project.database.ensure_role import EnsureRoleResult

        mock_ensure.return_value = EnsureRoleResult(outcome="created", role="odoo")
        config = MagicMock()
        with patch("dev_project.database.commands._logger") as mock_logger:
            code = run_database_command(
                OdpmCliArgs(
                    command="database",
                    database_subcommand="ensure-role",
                ),
                config,
            )
        self.assertEqual(code, 0)
        mock_ensure.assert_called_once_with(config)
        mock_logger.info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
