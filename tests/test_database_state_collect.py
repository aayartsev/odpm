"""Tests for database state collection and last_run persistence."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.database import (
    collect_database_state,
    ensure_database_dir_gitignore,
    last_run_missing,
    last_run_path,
    load_last_run,
    read_odoo_conf_db_fingerprint,
    save_last_run,
)
from dev_project.database.schema import DATABASE_LAST_RUN_SCHEMA_VERSION, DatabaseLastRun


class ReadOdooConfDbFingerprintTests(unittest.TestCase):
    def test_reads_values_from_odoo_conf(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf_path = Path(tmp) / "odoo.conf"
            conf_path.write_text(
                "\n".join(
                    [
                        "[options]",
                        "db_host = postgres",
                        "db_port = 5433",
                        "db_user = odoo",
                        "db_password = odoo",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fingerprint = read_odoo_conf_db_fingerprint(
                str(conf_path),
                default_host="db",
                default_port=5432,
                default_user="odoo",
            )
            self.assertEqual(fingerprint.db_host, "postgres")
            self.assertEqual(fingerprint.db_port, 5433)
            self.assertEqual(fingerprint.db_user, "odoo")

    def test_uses_defaults_when_conf_missing(self):
        fingerprint = read_odoo_conf_db_fingerprint(
            "/nonexistent/odoo.conf",
            default_host="db-dev",
            default_port=5432,
            default_user="odoo",
        )
        self.assertEqual(fingerprint.db_host, "db-dev")
        self.assertEqual(fingerprint.db_port, 5432)


class CollectDatabaseStateTests(unittest.TestCase):
    def _config(self, project_dir: str) -> MagicMock:
        data_path = os.path.join(
            project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR
        )
        config = MagicMock()
        config.project_dir = project_dir
        config.policy.scenario = constants.DEVELOPER_SCENARIO
        config.postgres_version = "17"
        config.postgres_data_local_storage = data_path
        config.user_env.postgres_service_name = "db-dev"
        config.user_env.postgres_port = 5432
        config.path_odoo_conf = os.path.join(project_dir, constants.ODOO_CONF_NAME)
        return config

    def test_collects_compose_and_odoo_conf_fingerprints(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "\n".join(
                    [
                        "[options]",
                        "db_host = db-dev",
                        "db_port = 5432",
                        "db_user = odoo",
                        "db_password = odoo",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            state = collect_database_state(self._config(project_dir))
            self.assertEqual(state.compose.service_name, "db-dev")
            self.assertEqual(state.compose.image_tag, "17")
            self.assertEqual(state.compose.host_port, 5432)
            self.assertEqual(state.odoo_conf.db_host, "db-dev")
            self.assertEqual(state.cluster.app_role, "odoo")
            self.assertIsNone(state.cluster.app_role_present)

    def test_collect_reports_db_host_mismatch_against_service_name(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "\n".join(
                    [
                        "[options]",
                        "db_host = db",
                        "db_port = 5432",
                        "db_user = odoo",
                        "db_password = odoo",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            state = collect_database_state(self._config(project_dir))
            self.assertEqual(state.compose.service_name, "db-dev")
            self.assertEqual(state.odoo_conf.db_host, "db")

    def test_detects_nonempty_data_dir_and_pg_major(self):
        with tempfile.TemporaryDirectory() as project_dir:
            data_path = Path(project_dir) / constants.POSTGRES_LOCAL_STORAGE_DIR
            data_path.mkdir(parents=True)
            (data_path / "PG_VERSION").write_text("17\n", encoding="utf-8")
            state = collect_database_state(self._config(project_dir))
            self.assertTrue(state.cluster.data_dir_nonempty)
            self.assertEqual(state.cluster.pg_major, 17)
            self.assertEqual(
                state.compose.data_path_abs,
                os.path.realpath(str(data_path)),
            )

    def test_empty_data_dir_reports_not_initialized(self):
        with tempfile.TemporaryDirectory() as project_dir:
            state = collect_database_state(self._config(project_dir))
            self.assertFalse(state.cluster.data_dir_nonempty)
            self.assertIsNone(state.cluster.pg_major)


class DatabaseLastRunPersistenceTests(unittest.TestCase):
    def _snapshot(self, data_path: str) -> DatabaseLastRun:
        from dev_project.database.schema import (
            DatabaseClusterFingerprint,
            DatabaseComposeFingerprint,
            DatabaseOdooConfFingerprint,
        )

        return DatabaseLastRun(
            schema_version=DATABASE_LAST_RUN_SCHEMA_VERSION,
            recorded_at="2026-06-17T20:00:00+00:00",
            odpm_scenario="developer",
            engine="postgres",
            compose=DatabaseComposeFingerprint(
                service_name="db",
                image_tag="17",
                data_path_abs=data_path,
                host_port=5432,
            ),
            odoo_conf=DatabaseOdooConfFingerprint(
                db_host="db",
                db_port=5432,
                db_user="odoo",
            ),
            cluster=DatabaseClusterFingerprint(
                data_dir_nonempty=True,
                pg_major=17,
                app_role="odoo",
                app_role_present=True,
            ),
        )

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as project_dir:
            data_path = os.path.join(project_dir, "data", "pg")
            snapshot = self._snapshot(data_path)
            save_last_run(project_dir, snapshot)
            self.assertFalse(last_run_missing(project_dir))
            loaded = load_last_run(project_dir)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded, snapshot)

    def test_ensure_database_dir_gitignore(self):
        with tempfile.TemporaryDirectory() as project_dir:
            ensure_database_dir_gitignore(project_dir)
            gitignore_path = Path(project_dir) / ".odpm" / "database" / ".gitignore"
            self.assertTrue(gitignore_path.is_file())
            self.assertIn("*", gitignore_path.read_text(encoding="utf-8"))

    def test_load_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertTrue(last_run_missing(project_dir))
            self.assertIsNone(load_last_run(project_dir))

    def test_saved_json_has_no_password(self):
        with tempfile.TemporaryDirectory() as project_dir:
            save_last_run(project_dir, self._snapshot("/tmp/pg"))
            raw = Path(last_run_path(project_dir)).read_text(encoding="utf-8")
            self.assertNotIn("password", raw.lower())
            payload = json.loads(raw)
            self.assertEqual(payload["schema_version"], DATABASE_LAST_RUN_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
