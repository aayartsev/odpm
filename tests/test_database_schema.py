"""Tests for database last_run schema serialization."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dev_project.database.schema import (
    DATABASE_LAST_RUN_SCHEMA_VERSION,
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseCurrentState,
    DatabaseLastRun,
    DatabaseOdooConfFingerprint,
)


class DatabaseSchemaTests(unittest.TestCase):
    def _sample_last_run(self) -> DatabaseLastRun:
        return DatabaseLastRun(
            schema_version=DATABASE_LAST_RUN_SCHEMA_VERSION,
            recorded_at="2026-06-17T20:00:00+00:00",
            odpm_scenario="developer",
            engine="postgres",
            compose=DatabaseComposeFingerprint(
                service_name="db-dev",
                image_tag="17",
                data_path_abs="/tmp/project/data/postgresql/var/lib/postgresql/data",
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
        )

    def test_round_trip_to_dict(self):
        snapshot = self._sample_last_run()
        restored = DatabaseLastRun.from_dict(snapshot.to_dict())
        self.assertEqual(restored, snapshot)

    def test_rejects_unsupported_schema_version(self):
        payload = self._sample_last_run().to_dict()
        payload["schema_version"] = 99
        with self.assertRaises(ValueError) as ctx:
            DatabaseLastRun.from_dict(payload)
        self.assertIn("schema_version", str(ctx.exception))

    def test_rejects_unsupported_engine(self):
        payload = self._sample_last_run().to_dict()
        payload["engine"] = "mysql"
        with self.assertRaises(ValueError) as ctx:
            DatabaseLastRun.from_dict(payload)
        self.assertIn("engine", str(ctx.exception))

    def test_cluster_optional_fields_omitted_in_json(self):
        cluster = DatabaseClusterFingerprint(
            data_dir_nonempty=False,
            pg_major=None,
            app_role="odoo",
            app_role_present=None,
        )
        payload = cluster.to_dict()
        self.assertNotIn("pg_major", payload)
        self.assertNotIn("app_role_present", payload)
        restored = DatabaseClusterFingerprint.from_dict(payload)
        self.assertEqual(restored.pg_major, None)
        self.assertEqual(restored.app_role_present, None)

    def test_current_state_to_last_run(self):
        current = DatabaseCurrentState(
            odpm_scenario="developer",
            engine="postgres",
            compose=self._sample_last_run().compose,
            odoo_conf=self._sample_last_run().odoo_conf,
            cluster=DatabaseClusterFingerprint(
                data_dir_nonempty=True,
                pg_major=17,
                app_role="odoo",
                app_role_present=None,
            ),
        )
        snapshot = current.to_last_run(recorded_at="2026-06-17T21:00:00+00:00")
        self.assertEqual(snapshot.recorded_at, "2026-06-17T21:00:00+00:00")
        self.assertEqual(snapshot.compose.service_name, "db-dev")

    def test_sample_payload_has_no_password_fields(self):
        payload = self._sample_last_run().to_dict()
        serialized = json.dumps(payload)
        self.assertNotIn("password", serialized.lower())


if __name__ == "__main__":
    unittest.main()
