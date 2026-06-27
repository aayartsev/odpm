"""Contract tests for R7 pre-release 4.7.0-beta on 4.7.0-dev."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import dev_project.constants as constants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(
    constants.RELEASE_VERSION == "4.7.0-beta",
    "R7 prerelease prep applies only when RELEASE_VERSION is 4.7.0-beta",
)
class ReleasePrereleaseR7Tests(unittest.TestCase):
    def test_release_version_is_prerelease_4_7_0_beta(self):
        self.assertEqual(constants.RELEASE_VERSION, "4.7.0-beta")
        self.assertEqual(constants.LATEST_STABLE_RELEASE, "4.6.0")
        self.assertEqual(constants.ODPM_VERSION, constants.RELEASE_VERSION)

    def test_release_lines_documents_47_dev_line(self):
        text = (PROJECT_ROOT / "docs/contributing/release-lines.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("4.7.0-dev", text)
        self.assertIn("`4.7.0-beta`", text)
        self.assertIn("4.7.x", text)

    def test_rpm_spec_prerelease_release(self):
        spec = (PROJECT_ROOT / "packaging/odpm.spec").read_text(encoding="utf-8")
        self.assertIn("%global version 4.7.0", spec)
        self.assertIn("%global release beta", spec)

    def test_debian_changelog_prerelease_line(self):
        changelog = (PROJECT_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
        self.assertRegex(changelog, r"^odpm \(4\.7\.0~beta-1\)", re.MULTILINE)


if __name__ == "__main__":
    unittest.main()
