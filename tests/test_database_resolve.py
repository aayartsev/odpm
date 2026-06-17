"""Tests for interactive and non-interactive database drift resolution."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.database import save_last_run
from dev_project.database.resolve import (
    ensure_no_blocking_database_drift,
    resolve_database_drifts,
)
from dev_project.database.schema import (
    DATABASE_LAST_RUN_SCHEMA_VERSION,
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseLastRun,
    DatabaseOdooConfFingerprint,
)
from dev_project.errors import PipelineError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.prepare import make_prepare_context
from dev_project.scenario_policy import ScenarioPolicy


class DatabaseResolveTests(unittest.TestCase):
    def _config(self, project_dir: str) -> MagicMock:
        data_path = os.path.join(
            project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR
        )
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.postgres_version = "17"
        config.postgres_data_local_storage = data_path
        config.user_env.postgres_service_name = "db-dev"
        config.user_env.postgres_port = 5432
        config.path_odoo_conf = os.path.join(project_dir, constants.ODOO_CONF_NAME)
        return config

    def _ctx(self, config: MagicMock, *, accept: tuple[str, ...] = ()) -> MagicMock:
        return make_prepare_context(
            config,
            MagicMock(),
            MagicMock(),
            OdpmCliArgs(accept_database_drift=accept),
        )

    def _write_odoo_conf(self, project_dir: str, *, db_host: str = "db-dev") -> None:
        Path(project_dir, constants.ODOO_CONF_NAME).write_text(
            "\n".join(
                [
                    "[options]",
                    f"db_host = {db_host}",
                    "db_port = 5432",
                    "db_user = odoo",
                    "db_password = odoo",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _last_run(self, project_dir: str, *, data_path: str) -> None:
        save_last_run(
            project_dir,
            DatabaseLastRun(
                schema_version=DATABASE_LAST_RUN_SCHEMA_VERSION,
                recorded_at="2026-06-17T20:00:00+00:00",
                odpm_scenario="developer",
                engine="postgres",
                compose=DatabaseComposeFingerprint(
                    service_name="db-dev",
                    image_tag="17",
                    data_path_abs=data_path,
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
                    app_role_present=True,
                ),
            ),
        )

    @patch("dev_project.database.status.probe_postgres_container_running", return_value=False)
    def test_non_interactive_blocking_drift_raises(self, _mock_running):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir)
            old_data = os.path.join(project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR)
            os.makedirs(old_data, exist_ok=True)
            (Path(old_data) / "PG_VERSION").write_text("17\n", encoding="utf-8")
            self._last_run(project_dir, data_path=old_data)
            other_data = os.path.join(project_dir, "other", "pg")
            os.makedirs(other_data, exist_ok=True)
            (Path(other_data) / "PG_VERSION").write_text("17\n", encoding="utf-8")
            config.postgres_data_local_storage = other_data
            with patch("dev_project.database.resolve.stdin_is_interactive", return_value=False):
                with self.assertRaises(PipelineError):
                    resolve_database_drifts(self._ctx(config))

    @patch("dev_project.database.status.probe_postgres_container_running", return_value=False)
    def test_accept_flag_allows_blocking_drift(self, _mock_running):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir)
            old_data = os.path.join(project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR)
            os.makedirs(old_data, exist_ok=True)
            (Path(old_data) / "PG_VERSION").write_text("17\n", encoding="utf-8")
            self._last_run(project_dir, data_path=old_data)
            other_data = os.path.join(project_dir, "other", "pg")
            os.makedirs(other_data, exist_ok=True)
            (Path(other_data) / "PG_VERSION").write_text("17\n", encoding="utf-8")
            config.postgres_data_local_storage = other_data
            with patch("dev_project.database.resolve.stdin_is_interactive", return_value=False):
                resolve_database_drifts(
                    self._ctx(config, accept=("data_path",))
                )
            ensure_no_blocking_database_drift(
                config, OdpmCliArgs(accept_database_drift=("data_path",))
            )

    @patch("dev_project.database.resolve.ensure_app_role")
    @patch("dev_project.database.status.probe_app_role_exists")
    @patch("dev_project.database.status.probe_postgres_ready", return_value=True)
    @patch("dev_project.database.status.probe_postgres_container_running", return_value=True)
    def test_interactive_app_role_missing_runs_ensure_role(
        self,
        _mock_running,
        _mock_ready,
        mock_role,
        mock_ensure,
    ):
        mock_role.side_effect = [False, True]
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir)
            ctx = self._ctx(config)
            with patch(
                "dev_project.database.resolve.stdin_is_interactive",
                return_value=True,
            ), patch(
                "dev_project.database.resolve.prompt_input",
                return_value="b",
            ):
                resolve_database_drifts(ctx)
            mock_ensure.assert_called_once_with(config)

    @patch("dev_project.database.status.probe_postgres_container_running", return_value=False)
    def test_interactive_abort_raises(self, _mock_running):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir)
            old_data = os.path.join(project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR)
            os.makedirs(old_data, exist_ok=True)
            (Path(old_data) / "PG_VERSION").write_text("17\n", encoding="utf-8")
            self._last_run(project_dir, data_path=old_data)
            other_data = os.path.join(project_dir, "other", "pg")
            os.makedirs(other_data, exist_ok=True)
            (Path(other_data) / "PG_VERSION").write_text("17\n", encoding="utf-8")
            config.postgres_data_local_storage = other_data
            with patch(
                "dev_project.database.resolve.stdin_is_interactive",
                return_value=True,
            ), patch(
                "dev_project.database.resolve.prompt_input",
                return_value="a",
            ):
                with self.assertRaises(PipelineError):
                    resolve_database_drifts(self._ctx(config))


if __name__ == "__main__":
    unittest.main()
