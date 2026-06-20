"""Release package version contract (deb/rpm vs manifest)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from dev_project import constants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ReleasePackagingVersionTests(unittest.TestCase):
    def test_manager_and_release_versions_differ_by_design(self):
        self.assertEqual(constants.ODPM_VERSION, "4.4")
        self.assertEqual(constants.RELEASE_VERSION, "4.4.2")
        self.assertEqual(constants.MANIFEST_V1_CONTRACT_LINE, "4.0")

    def test_debian_changelog_matches_release_line(self):
        changelog = (PROJECT_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
        self.assertRegex(changelog, r"^odpm \(4\.4\.2-1\)", re.MULTILINE)

    def test_rpm_spec_matches_release_line(self):
        spec = (PROJECT_ROOT / "packaging" / "odpm.spec").read_text(encoding="utf-8")
        self.assertIn("Version:        4.4.2", spec)
        self.assertIn("Release:        1%{?dist}", spec)

    def test_release_version_parses_for_rpm(self):
        match = re.fullmatch(
            r"(\d+(?:\.\d+)*)(?:-(.+))?", constants.RELEASE_VERSION
        )
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), "4.4.2")
        self.assertIsNone(match.group(2))


if __name__ == "__main__":
    unittest.main()
