"""Release package version contract (deb/rpm, pip, CLI)."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from scripts.verify_release_tag_version import verify_release_tag_version
from tests.odpm_subprocess import run_odpm

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ReleasePackagingVersionTests(unittest.TestCase):
    def test_odpm_version_aliases_release_version(self):
        self.assertEqual(constants.ODPM_VERSION, constants.RELEASE_VERSION)
        self.assertEqual(constants.RELEASE_VERSION, "4.4.2-beta")

    def test_manifest_contract_line_stays_separate_from_product_version(self):
        self.assertEqual(constants.MANIFEST_V1_CONTRACT_LINE, "4.0")
        self.assertNotEqual(constants.MANIFEST_V1_CONTRACT_LINE, constants.RELEASE_VERSION)

    def test_cli_version_matches_release_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = run_odpm("--version", cwd=tmp)
        self.assertEqual(completed.returncode, 0, msg=completed.stderr or completed.stdout)
        self.assertIn(
            f"odpm version: {constants.RELEASE_VERSION}",
            completed.stderr + completed.stdout,
        )

    def test_debian_changelog_matches_release_line(self):
        changelog = (PROJECT_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
        release = re.escape(constants.RELEASE_VERSION)
        self.assertRegex(changelog, rf"^odpm \({release}-1\)", re.MULTILINE)

    def test_rpm_spec_matches_release_line(self):
        spec = (PROJECT_ROOT / "packaging" / "odpm.spec").read_text(encoding="utf-8")
        self.assertIn(f"Version:        {constants.RELEASE_VERSION}", spec)
        self.assertIn("Release:        1%{?dist}", spec)

    def test_release_version_parses_for_rpm(self):
        match = re.fullmatch(
            r"(\d+(?:\.\d+)*)(?:-(.+))?", constants.RELEASE_VERSION
        )
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), constants.RELEASE_VERSION)
        self.assertIsNone(match.group(2))

    def test_release_tag_matches_release_version(self):
        verify_release_tag_version(constants.RELEASE_VERSION)

    def test_release_tag_mismatch_raises(self):
        with self.assertRaises(ValueError):
            verify_release_tag_version("0.0.0")


if __name__ == "__main__":
    unittest.main()
