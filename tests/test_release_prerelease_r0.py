"""Contract tests for R0 pre-release 4.6.0-beta on 4.6.0-dev."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import dev_project.constants as constants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(
    constants.RELEASE_VERSION == "4.6.0-beta",
    "R0 prerelease prep applies only when RELEASE_VERSION is 4.6.0-beta",
)
class ReleasePrereleaseR0Tests(unittest.TestCase):
    def test_release_version_is_prerelease_4_6_0_beta(self):
        self.assertEqual(constants.RELEASE_VERSION, "4.6.0-beta")
        self.assertEqual(constants.LATEST_STABLE_RELEASE, "4.5.0")
        self.assertEqual(constants.ODPM_VERSION, constants.RELEASE_VERSION)

    def test_release_lines_documents_46_dev_line(self):
        text = (PROJECT_ROOT / "docs/contributing/release-lines.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("4.6.0-dev", text)
        self.assertIn("`4.6.0-beta`", text)
        self.assertIn("заморожена", text)
        self.assertIn("4.5.x", text)

    def test_rpm_spec_prerelease_release(self):
        spec = (PROJECT_ROOT / "packaging" / "odpm.spec").read_text(encoding="utf-8")
        self.assertIn("%global version 4.6.0", spec)
        self.assertIn("%global release beta", spec)

    def test_debian_changelog_prerelease_line(self):
        changelog = (PROJECT_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
        self.assertRegex(changelog, r"^odpm \(4\.6\.0~beta-1\)", re.MULTILINE)


if __name__ == "__main__":
    unittest.main()
