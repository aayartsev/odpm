"""Tests for database configuration drift detection."""

from __future__ import annotations

import unittest

from dev_project.database.drift import (
    DatabaseDrift,
    detect_database_drift,
    has_blocking_database_drift,
)
from dev_project.database.schema import (
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseCurrentState,
    DatabaseLastRun,
    DatabaseOdooConfFingerprint,
)


def _current(
    *,
    service_name: str = "db-dev",
    db_host: str = "db-dev",
    image_tag: str = "17",
    data_path: str = "/tmp/project/data/pg",
    host_port: int = 5432,
    scenario: str = "developer",
    data_dir_nonempty: bool = True,
    pg_major: int | None = 17,
) -> DatabaseCurrentState:
    return DatabaseCurrentState(
        odpm_scenario=scenario,
        engine="postgres",
        compose=DatabaseComposeFingerprint(
            service_name=service_name,
            image_tag=image_tag,
            data_path_abs=data_path,
            host_port=host_port,
        ),
        odoo_conf=DatabaseOdooConfFingerprint(
            db_host=db_host,
            db_port=5432,
            db_user="odoo",
        ),
        cluster=DatabaseClusterFingerprint(
            data_dir_nonempty=data_dir_nonempty,
            pg_major=pg_major,
            app_role="odoo",
            app_role_present=None,
        ),
    )


def _last_run(
    *,
    service_name: str = "db-dev",
    image_tag: str = "17",
    data_path: str = "/tmp/project/data/pg",
    host_port: int = 5432,
    scenario: str = "developer",
    data_dir_nonempty: bool = True,
    pg_major: int | None = 17,
) -> DatabaseLastRun:
    return DatabaseLastRun(
        schema_version=1,
        recorded_at="2026-06-17T20:00:00+00:00",
        odpm_scenario=scenario,
        engine="postgres",
        compose=DatabaseComposeFingerprint(
            service_name=service_name,
            image_tag=image_tag,
            data_path_abs=data_path,
            host_port=host_port,
        ),
        odoo_conf=DatabaseOdooConfFingerprint(
            db_host=service_name,
            db_port=5432,
            db_user="odoo",
        ),
        cluster=DatabaseClusterFingerprint(
            data_dir_nonempty=data_dir_nonempty,
            pg_major=pg_major,
            app_role="odoo",
            app_role_present=True,
        ),
    )


class DatabaseDriftDetectionTests(unittest.TestCase):
    def test_first_run_emits_info_drift_only_when_aligned(self):
        drifts = detect_database_drift(_current(), None)
        kinds = {drift.kind for drift in drifts}
        self.assertEqual(kinds, {"first_run"})

    def test_db_host_mismatch_without_last_run(self):
        drifts = detect_database_drift(_current(service_name="db-dev", db_host="db"), None)
        kinds = [drift.kind for drift in drifts]
        self.assertEqual(kinds, ["first_run", "db_host_mismatch"])
        mismatch = drifts[1]
        self.assertEqual(mismatch.previous, "db-dev")
        self.assertEqual(mismatch.current, "db")
        self.assertEqual(mismatch.severity, "low")

    def test_service_name_drift(self):
        drifts = detect_database_drift(
            _current(service_name="db-dev", db_host="db-dev"),
            _last_run(service_name="db"),
        )
        self.assertIn(
            DatabaseDrift(
                kind="service_name",
                severity="low",
                previous="db",
                current="db-dev",
            ),
            drifts,
        )

    def test_data_path_drift_is_high_severity(self):
        drifts = detect_database_drift(
            _current(data_path="/tmp/new/pg"),
            _last_run(data_path="/tmp/old/pg"),
        )
        drift = next(drift for drift in drifts if drift.kind == "data_path")
        self.assertEqual(drift.severity, "high")
        self.assertTrue(has_blocking_database_drift(drifts))

    def test_postgres_major_drift_is_high_severity(self):
        drifts = detect_database_drift(
            _current(image_tag="17"),
            _last_run(image_tag="13"),
        )
        drift = next(drift for drift in drifts if drift.kind == "postgres_major")
        self.assertEqual(drift.previous, "13")
        self.assertEqual(drift.current, "17")
        self.assertTrue(has_blocking_database_drift(drifts))

    def test_host_port_drift(self):
        drifts = detect_database_drift(
            _current(host_port=5433),
            _last_run(host_port=5432),
        )
        self.assertIn(
            DatabaseDrift(
                kind="host_port",
                severity="low",
                previous="5432",
                current="5433",
            ),
            drifts,
        )

    def test_odpm_scenario_drift(self):
        drifts = detect_database_drift(
            _current(scenario="server"),
            _last_run(scenario="developer"),
        )
        self.assertIn(
            DatabaseDrift(
                kind="odpm_scenario",
                severity="medium",
                previous="developer",
                current="server",
            ),
            drifts,
        )

    def test_data_dir_empty_changed_drift(self):
        drifts = detect_database_drift(
            _current(data_dir_nonempty=False, pg_major=None),
            _last_run(data_dir_nonempty=True, pg_major=17),
        )
        self.assertIn(
            DatabaseDrift(
                kind="data_dir_empty_changed",
                severity="medium",
                previous="True",
                current="False",
            ),
            drifts,
        )

    def test_no_drift_when_snapshots_match(self):
        state = _current()
        drifts = detect_database_drift(state, _last_run())
        self.assertEqual(drifts, ())

    def test_rename_service_and_stale_odoo_conf_emits_both_drifts(self):
        drifts = detect_database_drift(
            _current(service_name="db-dev", db_host="db"),
            _last_run(service_name="db"),
        )
        kinds = {drift.kind for drift in drifts}
        self.assertEqual(kinds, {"service_name", "db_host_mismatch"})

    def test_app_role_missing_when_probe_reports_false(self):
        state = _current()
        state = DatabaseCurrentState(
            odpm_scenario=state.odpm_scenario,
            engine=state.engine,
            compose=state.compose,
            odoo_conf=state.odoo_conf,
            cluster=DatabaseClusterFingerprint(
                data_dir_nonempty=state.cluster.data_dir_nonempty,
                pg_major=state.cluster.pg_major,
                app_role="odoo",
                app_role_present=False,
            ),
        )
        drifts = detect_database_drift(state, _last_run())
        self.assertIn(
            DatabaseDrift(
                kind="app_role_missing",
                severity="high",
                previous="",
                current="odoo",
            ),
            drifts,
        )

    def test_reason_id_is_stable(self):
        drift = DatabaseDrift(
            kind="data_path",
            severity="high",
            previous="/a",
            current="/b",
        )
        self.assertEqual(drift.reason_id, "database.drift.data_path")


if __name__ == "__main__":
    unittest.main()
