"""Tests for manifest v1→v2 migrator."""

from __future__ import annotations

import copy
import unittest

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.git.deps_lock import DepsLock, LockEntry
from dev_project.manifest.database import database_block_from_user_settings
from dev_project.manifest.migrator import (
    format_manifest_migration_diff,
    migrate_v1_flat_to_v2,
)
from dev_project.manifest.schema import validate_manifest_v2


def _minimal_v1(**overrides) -> dict:
    payload = {
        "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
        "odoo_version": "17.0",
        "python_version": "3.12",
        "distro_name": "debian",
        "distro_version": "12",
        "postgres_version": "16",
        "odoo_git_link": "https://github.com/odoo/odoo.git 17.0",
        "dependencies": [],
        "requirements_txt": [],
    }
    payload.update(overrides)
    return payload


class DatabaseBlockFromUserSettingsTests(unittest.TestCase):
    def test_maps_lang_and_country(self):
        block = database_block_from_user_settings(
            {"db_creation_data": {"db_lang": "ru_RU", "db_country_code": "RU"}}
        )
        self.assertEqual(block, {"language": "ru_RU", "country": "RU"})


class MigrateV1FlatToV2Tests(unittest.TestCase):
    def test_maps_core_fields(self):
        v2 = migrate_v1_flat_to_v2(_minimal_v1())
        validate_manifest_v2(v2)
        self.assertEqual(v2["manifest_schema"], 2)
        self.assertEqual(v2["requires_odpm"], constants.ODPM_VERSION)
        self.assertEqual(v2["python"], "3.12")
        self.assertEqual(v2["distro"]["name"], "debian")
        self.assertEqual(v2["postgres"], "16")
        self.assertEqual(v2["platform"]["git"], "https://github.com/odoo/odoo.git 17.0")
        self.assertEqual(v2["odoo_version"], "17.0")

    def test_prefers_manifest_database_over_user_settings(self):
        v2 = migrate_v1_flat_to_v2(
            _minimal_v1(database={"language": "de_DE", "country": "DE"}),
            user_settings={
                "db_creation_data": {"db_lang": "ru_RU", "db_country_code": "RU"}
            },
        )
        self.assertEqual(v2["database"]["language"], "de_DE")

    def test_copies_database_from_user_settings_when_missing_in_manifest(self):
        v2 = migrate_v1_flat_to_v2(
            _minimal_v1(),
            user_settings={
                "db_creation_data": {"db_lang": "ru_RU", "db_country_code": "RU"}
            },
        )
        self.assertEqual(v2["database"]["language"], "ru_RU")

    def test_copies_locks_from_deps_lock(self):
        lock = DepsLock(
            platform=LockEntry(
                url="https://github.com/odoo/odoo.git",
                commit="a" * 40,
            ),
            dependencies=[
                LockEntry(
                    url="https://github.com/OCA/web.git",
                    commit="b" * 40,
                )
            ],
        )
        v2 = migrate_v1_flat_to_v2(_minimal_v1(), deps_lock=lock)
        self.assertEqual(
            v2["locks"]["git"]["https://github.com/odoo/odoo.git"],
            "a" * 40,
        )
        self.assertEqual(
            v2["locks"]["git"]["https://github.com/OCA/web.git"],
            "b" * 40,
        )

    def test_developing_from_user_settings(self):
        v2 = migrate_v1_flat_to_v2(
            _minimal_v1(),
            user_settings={"developing_project": "https://github.com/acme/demo.git"},
        )
        self.assertEqual(
            v2["developing"]["git"],
            "https://github.com/acme/demo.git",
        )

    def test_already_v2_raises(self):
        with self.assertRaises(ConfigError):
            migrate_v1_flat_to_v2(
                {
                    "manifest_schema": 2,
                    "requires_odpm": "4.4",
                    "platform": {"git": "https://github.com/odoo/odoo.git 17.0"},
                    "python": "3.12",
                    "distro": {"name": "debian", "version": "12"},
                    "postgres": "16",
                }
            )


class ManifestMigrationDiffTests(unittest.TestCase):
    def test_diff_contains_v2_keys(self):
        before = _minimal_v1()
        after = migrate_v1_flat_to_v2(copy.deepcopy(before))
        diff = format_manifest_migration_diff("/tmp/odpm.json", before, after)
        self.assertIn("manifest_schema", diff)
        self.assertIn('"requires_odpm": "4.4"', diff)


if __name__ == "__main__":
    unittest.main()
