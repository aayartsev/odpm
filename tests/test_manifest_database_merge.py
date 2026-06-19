"""Tests for manifest database block merge into db_creation_data."""

from __future__ import annotations

import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config.bootstrap_phases import (
    _apply_manifest_database_to_user_settings,
    load_project_settings,
)
from dev_project.config.state import UserSettingsState
from dev_project.manifest.database import (
    database_creation_overrides_from_manifest,
    merge_db_creation_from_manifest,
)
from dev_project.manifest.reader import ManifestView, load_manifest


class DatabaseOverridesFromManifestTests(unittest.TestCase):
    def test_maps_language_and_country(self):
        overrides = database_creation_overrides_from_manifest(
            {"database": {"language": "ru_RU", "country": "RU"}}
        )
        self.assertEqual(
            overrides,
            {"db_lang": "ru_RU", "db_country_code": "RU"},
        )

    def test_country_null_and_false_preserved(self):
        self.assertEqual(
            database_creation_overrides_from_manifest(
                {"database": {"language": "en_US", "country": None}}
            )["db_country_code"],
            None,
        )
        self.assertFalse(
            database_creation_overrides_from_manifest(
                {"database": {"language": "en_US", "country": False}}
            )["db_country_code"]
        )

    def test_missing_database_block_returns_empty(self):
        self.assertEqual(database_creation_overrides_from_manifest({}), {})
        self.assertEqual(
            database_creation_overrides_from_manifest({"odoo_version": "17.0"}),
            {},
        )

    def test_language_only(self):
        overrides = database_creation_overrides_from_manifest(
            {"database": {"language": "de_DE"}}
        )
        self.assertEqual(overrides, {"db_lang": "de_DE"})


class MergeDbCreationFromManifestTests(unittest.TestCase):
    def test_manifest_overrides_user_settings(self):
        merged = merge_db_creation_from_manifest(
            {"db_lang": "en_US", "db_country_code": "US", "create_demo": True},
            {"database": {"language": "ru_RU", "country": "RU"}},
        )
        self.assertEqual(merged["db_lang"], "ru_RU")
        self.assertEqual(merged["db_country_code"], "RU")
        self.assertTrue(merged["create_demo"])

    def test_user_settings_kept_when_manifest_has_no_database(self):
        user = {"db_lang": "fr_FR", "create_demo": False}
        self.assertIs(
            merge_db_creation_from_manifest(user, {"odoo_version": "17.0"}),
            user,
        )


class LoadManifestDatabaseSchemaTests(unittest.TestCase):
    def test_v2_accepts_database_block(self):
        raw = {
            "manifest_schema": 2,
            "requires_odpm": "4.4",
            "platform": {"git": "https://github.com/odoo/odoo.git 19.0"},
            "python": "3.12",
            "distro": {"name": "debian", "version": "13"},
            "postgres": "15",
            "database": {"language": "ru_RU", "country": "RU"},
        }
        view = load_manifest(raw)
        self.assertEqual(
            view.source_raw["database"],
            {"language": "ru_RU", "country": "RU"},
        )

    def test_v1_accepts_database_block(self):
        raw = {
            "odpm_version": "4.0",
            "odoo_version": "17.0",
            "database": {"language": "pl_PL", "country": "PL"},
        }
        view = load_manifest(deepcopy(raw))
        self.assertEqual(view.source_raw["database"]["language"], "pl_PL")


class ApplyManifestDatabaseBootstrapTests(unittest.TestCase):
    def test_apply_updates_user_slice(self):
        config = MagicMock()
        config._user = UserSettingsState(
            db_creation_data={"db_lang": "en_US", "db_country_code": "US"},
        )
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm="4.4",
            raw_normalized={},
            source_raw={"database": {"language": "ru_RU", "country": "RU"}},
        )

        _apply_manifest_database_to_user_settings(config)

        self.assertEqual(config._user.db_creation_data["db_lang"], "ru_RU")
        self.assertEqual(config._user.db_creation_data["db_country_code"], "RU")

    def test_no_manifest_view_is_noop(self):
        config = MagicMock()
        original = {"db_lang": "en_US"}
        config._user = UserSettingsState(db_creation_data=dict(original))
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = None

        _apply_manifest_database_to_user_settings(config)

        self.assertEqual(config._user.db_creation_data, original)


class LoadProjectSettingsDatabaseMergeTests(unittest.TestCase):
    def test_load_project_settings_merges_manifest_database(self):
        from dev_project.config.bootstrap_context import OdooBuildDateResolver
        from dev_project.host.cli.args import OdpmCliArgs

        config = MagicMock()
        config._user = UserSettingsState(
            db_creation_data={"db_lang": "en_US", "db_country_code": "US"},
        )
        config._raw_odpm_json = {
            "odoo_version": "18.0",
            "python_version": "3.12",
            "platform_name": "odoo",
            "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
            "odoo_build_date": constants.ODOO_DEFAULT_BUILD_DATE,
        }
        config.arguments = OdpmCliArgs(
            odoo_version=None,
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
        )
        config._project = MagicMock()
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V1,
            requires_odpm=None,
            raw_normalized=config._raw_odpm_json,
            source_raw={
                **config._raw_odpm_json,
                "database": {"language": "ru_RU", "country": "RU"},
            },
        )
        config.bootstrap.repo_odpm_json = "/tmp/project/odpm.json"
        ctx = MagicMock()
        ctx.build_date = OdooBuildDateResolver(config)
        config._bootstrap_ctx = ctx
        config.pd_manager = MagicMock(
            project_docker_compose_template_path="/tmp/project/.odpm/docker-compose.yml"
        )

        with patch("dev_project.config.bootstrap_phases.os.path.exists", return_value=True):
            load_project_settings(config)

        self.assertEqual(config._user.db_creation_data["db_lang"], "ru_RU")
        self.assertEqual(config._user.db_creation_data["db_country_code"], "RU")


if __name__ == "__main__":
    unittest.main()
