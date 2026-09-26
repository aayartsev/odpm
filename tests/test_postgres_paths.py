"""Unit tests for PostgreSQL 18+ Docker volume layout helpers."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.compose.compose_document import build_compose_document
from dev_project.compose.service_names import LOGICAL_POSTGRES_VOLUME
from dev_project.config.paths import ConfigPaths
from dev_project.database.postgres_paths import (
    parse_postgres_major,
    postgres_cluster_dir_on_host,
    postgres_container_mount_path,
    postgres_local_storage_relpath,
    postgres_pgdata_path,
    uses_postgres_v18_docker_layout,
)
from tests.fixtures.compose.golden_scenario_env import make_golden_compose_env


class PostgresPathsHelpersTests(unittest.TestCase):
    def test_parse_and_layout_flags(self):
        self.assertEqual(parse_postgres_major("18"), 18)
        self.assertEqual(parse_postgres_major("16.4"), 16)
        self.assertFalse(uses_postgres_v18_docker_layout("17"))
        self.assertTrue(uses_postgres_v18_docker_layout("18"))

    def test_legacy_paths(self):
        self.assertEqual(
            postgres_container_mount_path("16"),
            "/var/lib/postgresql/data",
        )
        self.assertEqual(
            postgres_pgdata_path("16"),
            "/var/lib/postgresql/data",
        )
        self.assertEqual(
            postgres_local_storage_relpath("16"),
            constants.POSTGRES_LOCAL_STORAGE_DIR,
        )
        self.assertEqual(
            postgres_cluster_dir_on_host("/data", "16"),
            "/data",
        )

    def test_v18_paths(self):
        self.assertEqual(
            postgres_container_mount_path("18"),
            "/var/lib/postgresql",
        )
        self.assertEqual(
            postgres_pgdata_path("18"),
            "/var/lib/postgresql/18/docker",
        )
        self.assertEqual(
            postgres_local_storage_relpath("18"),
            "data/postgresql/var/lib/postgresql",
        )
        self.assertEqual(
            postgres_cluster_dir_on_host("/data", "18"),
            os.path.join("/data", "18", "docker"),
        )


class Postgres18ComposeDocumentTests(unittest.TestCase):
    def test_compose_mount_legacy_for_postgres_16(self):
        env = make_golden_compose_env(constants.DEVELOPER_SCENARIO)
        env.config.postgres_version = "16"
        document = build_compose_document(env)
        volumes = document["services"]["db"]["volumes"]
        self.assertEqual(
            volumes, [f"{LOGICAL_POSTGRES_VOLUME}:/var/lib/postgresql/data"]
        )

    def test_compose_mount_parent_for_postgres_18(self):
        env = make_golden_compose_env(constants.DEVELOPER_SCENARIO)
        env.config.postgres_version = "18"
        document = build_compose_document(env)
        volumes = document["services"]["db"]["volumes"]
        self.assertEqual(volumes, [f"{LOGICAL_POSTGRES_VOLUME}:/var/lib/postgresql"])


class PostgresLocalStoragePathTests(unittest.TestCase):
    def test_config_paths_uses_v18_relpath(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.postgres_version = "18"
            config.pd_manager = MagicMock()
            config.pd_manager.project_path = project_dir
            path = ConfigPaths(config).get_postgres_data_local_storage_path()
            self.assertTrue(path.endswith("data/postgresql/var/lib/postgresql"))
            self.assertTrue(Path(path).is_dir())


if __name__ == "__main__":
    unittest.main()
