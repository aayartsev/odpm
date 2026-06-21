"""Tests for manifest schema detection and manager compatibility."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.manifest.compat import (
    assert_manager_supports_manifest,
    parse_manifest_version_info,
)


class ParseManifestVersionInfoTests(unittest.TestCase):
    def test_flat_manifest_defaults_to_schema_v1(self):
        info = parse_manifest_version_info({"odoo_version": "19.0"})
        self.assertEqual(info.manifest_schema, constants.MANIFEST_SCHEMA_V1)
        self.assertEqual(info.v1_contract_line, constants.DEFAULT_ODPM_VERSION)

    def test_flat_manifest_reads_odpm_version_contract_line(self):
        info = parse_manifest_version_info({"odpm_version": "4.0"})
        self.assertEqual(info.manifest_schema, constants.MANIFEST_SCHEMA_V1)
        self.assertEqual(info.v1_contract_line, "4.0")

    def test_v2_manifest_reads_requires_odpm(self):
        info = parse_manifest_version_info(
            {"manifest_schema": 2, "requires_odpm": "4.4"}
        )
        self.assertEqual(info.manifest_schema, constants.MANIFEST_SCHEMA_V2)
        self.assertEqual(info.requires_odpm, "4.4")
        self.assertIsNone(info.v1_contract_line)

    def test_explicit_manifest_schema_v1_reads_odpm_version(self):
        info = parse_manifest_version_info(
            {"manifest_schema": 1, "odpm_version": "4.0"}
        )
        self.assertEqual(info.manifest_schema, constants.MANIFEST_SCHEMA_V1)
        self.assertEqual(info.v1_contract_line, "4.0")


class AssertManagerSupportsManifestTests(unittest.TestCase):
    def test_v1_contract_4_0_accepted_by_manager_4_4(self):
        assert_manager_supports_manifest(
            {"odpm_version": "4.0"},
            manager_version="4.4",
        )

    def test_v1_contract_3_0_accepted_by_manager_4_4(self):
        assert_manager_supports_manifest(
            {"odpm_version": "3.0"},
            manager_version="4.4",
        )

    def test_missing_odpm_version_uses_legacy_3_0_compat(self):
        info = assert_manager_supports_manifest(
            {"odoo_version": "17.0"},
            manager_version="4.4",
        )
        self.assertEqual(info.manifest_schema, constants.MANIFEST_SCHEMA_V1)
        self.assertEqual(info.v1_contract_line, constants.DEFAULT_ODPM_VERSION)

    def test_v1_unsupported_contract_raises(self):
        with self.assertRaises(ConfigError):
            assert_manager_supports_manifest(
                {"odpm_version": "2.0"},
                manager_version="4.4",
            )

    def test_v2_requires_odpm_satisfied(self):
        assert_manager_supports_manifest(
            {"manifest_schema": 2, "requires_odpm": "4.4.0"},
            manager_version="4.4",
        )

    def test_v2_requires_odpm_newer_than_manager_raises(self):
        with self.assertRaises(ConfigError):
            assert_manager_supports_manifest(
                {"manifest_schema": 2, "requires_odpm": "4.5"},
                manager_version="4.4",
            )

    def test_v2_missing_requires_odpm_raises(self):
        with self.assertRaises(ConfigError):
            assert_manager_supports_manifest(
                {"manifest_schema": 2},
                manager_version="4.4",
            )

    def test_unsupported_manifest_schema_raises(self):
        with self.assertRaises(ConfigError):
            assert_manager_supports_manifest(
                {"manifest_schema": 99, "requires_odpm": "4.4"},
                manager_version="4.4",
            )

    def test_invalid_requires_odpm_raises(self):
        with self.assertRaises(ConfigError):
            assert_manager_supports_manifest(
                {"manifest_schema": 2, "requires_odpm": "not-a-version"},
                manager_version="4.4",
            )


if __name__ == "__main__":
    unittest.main()
