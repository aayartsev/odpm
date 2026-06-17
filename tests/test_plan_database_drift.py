"""Tests for database drift integration in odpm plan."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.database import save_last_run
from dev_project.database.schema import (
    DATABASE_LAST_RUN_SCHEMA_VERSION,
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseLastRun,
    DatabaseOdooConfFingerprint,
)
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.plan.database_preview import collect_database_drift_warnings
from dev_project.prepare import build_plan, make_prepare_context
from dev_project.prepare.steps_database import evaluate_database_drift
from dev_project.prepare.steps_template import evaluate_template_odoo_conf
from dev_project.scenario_policy import ScenarioPolicy


class PlanDatabaseDriftTests(unittest.TestCase):
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
        config.pd_manager.check_project_odoo_config_template.return_value = False
        return config

    def _ctx(self, config: MagicMock):
        return make_prepare_context(
            config, MagicMock(), MagicMock(), OdpmCliArgs(skip_start=True)
        )

    def _write_odoo_conf(self, project_dir: str, *, db_host: str) -> None:
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

    def _write_odoo_conf_template(self, project_dir: str) -> None:
        template_path = Path(
            project_dir, constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH
        )
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(
            "\n".join(
                [
                    "[options]",
                    constants.DO_NOT_CHANGE_PARAM,
                    constants.ADMIN_PASSWD_MESSAGE,
                    f"db_user = {constants.POSTGRES_ODOO_USER_MARKER}",
                    f"db_password = {constants.POSTGRES_ODOO_PASS_MARKER}",
                    f"db_host = {constants.POSTGRES_ODOO_HOST_MARKER}",
                    f"db_port = {constants.POSTGRES_ODOO_PORT_MARKER}",
                    f"http_port = {constants.ODOO_PORT_MARKER}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _last_run(self, project_dir: str, *, service_name: str = "db") -> None:
        data_path = os.path.join(
            project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR
        )
        save_last_run(
            project_dir,
            DatabaseLastRun(
                schema_version=DATABASE_LAST_RUN_SCHEMA_VERSION,
                recorded_at="2026-06-17T20:00:00+00:00",
                odpm_scenario="developer",
                engine="postgres",
                compose=DatabaseComposeFingerprint(
                    service_name=service_name,
                    image_tag="17",
                    data_path_abs=data_path,
                    host_port=5432,
                ),
                odoo_conf=DatabaseOdooConfFingerprint(
                    db_host=service_name,
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

    def test_template_odoo_conf_updates_on_db_host_mismatch(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf_template(project_dir)
            self._write_odoo_conf(project_dir, db_host="db")
            step = evaluate_template_odoo_conf(self._ctx(config))
            self.assertEqual(step.id, "template.odoo_conf")
            self.assertEqual(step.outcome, "update")
            self.assertIn("db-dev", step.reason)

    def test_database_drift_step_run_on_service_rename(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir, db_host="db-dev")
            self._last_run(project_dir, service_name="db")
            step = evaluate_database_drift(self._ctx(config))
            self.assertEqual(step.id, "database.drift")
            self.assertEqual(step.outcome, "run")
            self.assertIn("service_name", step.reason)

    def test_database_drift_step_noop_on_first_run_without_mismatch(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir, db_host="db-dev")
            step = evaluate_database_drift(self._ctx(config))
            self.assertEqual(step.outcome, "noop")

    def test_plan_warnings_include_db_host_mismatch(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir, db_host="db")
            warnings = collect_database_drift_warnings(config)
            self.assertTrue(
                any("db_host" in warning.lower() or "db-dev" in warning for warning in warnings)
            )

    def test_plan_warnings_include_blocking_for_data_path_drift(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir, db_host="db-dev")
            self._last_run(project_dir, service_name="db-dev")
            other_data = os.path.join(project_dir, "other", "pg")
            os.makedirs(other_data, exist_ok=True)
            (Path(other_data) / "PG_VERSION").write_text("17\n", encoding="utf-8")
            config.postgres_data_local_storage = other_data
            warnings = collect_database_drift_warnings(config)
            self.assertTrue(any("Blocking database" in w for w in warnings))
            step = evaluate_database_drift(self._ctx(config))
            self.assertTrue(step.required)

    def test_build_plan_includes_database_drift_step(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            self._write_odoo_conf(project_dir, db_host="db-dev")
            self._last_run(project_dir, service_name="db")
            ctx = self._ctx(config)
            plan = build_plan(config, OdpmCliArgs(skip_start=True), None)
            step_ids = [step.id for step in plan.steps]
            self.assertIn("database.drift", step_ids)
            self.assertTrue(any("PostgreSQL compose service" in w for w in plan.warnings))


if __name__ == "__main__":
    unittest.main()
