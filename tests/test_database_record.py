"""Tests for database last_run recording from the container checker."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from dev_project import constants
from dev_project.container_config.database_context import DatabaseContainerContext
from dev_project.database.record import record_last_run_from_container
from dev_project.database.schema import DATABASE_LAST_RUN_SCHEMA_VERSION
from dev_project.database.state import write_last_run_to_path

from tests.container_config_helpers import minimal_container_config


def _sample_database_context() -> DatabaseContainerContext:
    return DatabaseContainerContext(
        service_name="db-dev",
        image_tag="16",
        data_path_abs="/tmp/postgres-data",
        host_port=5432,
        data_dir_nonempty=True,
        pg_major=16,
        app_role=constants.POSTGRES_ODOO_USER,
        db_host="db-dev",
        db_port=5432,
        db_user=constants.POSTGRES_ODOO_USER,
    )


class WriteLastRunToPathTests(unittest.TestCase):
    def test_writes_json_snapshot(self):
        with tempfile.TemporaryDirectory() as project_dir:
            path = os.path.join(project_dir, "last_run.json")
            snapshot = _sample_database_context().to_last_run(
                constants.DEVELOPER_SCENARIO,
                app_role_present=True,
            )
            write_last_run_to_path(path, snapshot)
            loaded = json.loads(open(path, encoding="utf-8").read())
            self.assertEqual(loaded["schema_version"], DATABASE_LAST_RUN_SCHEMA_VERSION)
            self.assertEqual(loaded["compose"]["service_name"], "db-dev")
            self.assertTrue(loaded["cluster"]["app_role_present"])


class RecordLastRunFromContainerTests(unittest.TestCase):
    def test_records_snapshot_when_database_context_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "last_run.json")
            config = minimal_container_config(
                odpm_scenario=constants.DEVELOPER_SCENARIO,
                database=_sample_database_context().to_dict(),
            )
            with patch(
                "dev_project.database.record.constants.ODPM_DATABASE_LAST_RUN_CONTAINER_PATH",
                target,
            ):
                written = record_last_run_from_container(config)
            self.assertEqual(written, target)
            loaded = json.loads(open(target, encoding="utf-8").read())
            self.assertEqual(loaded["compose"]["service_name"], "db-dev")
            self.assertTrue(loaded["cluster"]["app_role_present"])

    def test_skips_when_database_context_missing(self):
        config = minimal_container_config()
        self.assertIsNone(record_last_run_from_container(config))


if __name__ == "__main__":
    unittest.main()
