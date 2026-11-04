"""Contract tests for R8 pre-release 4.8.0-beta on 4.8.0-dev."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import dev_project.constants as constants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(
    constants.RELEASE_VERSION == "4.8.0-beta",
    "R8 prerelease prep applies only when RELEASE_VERSION is 4.8.0-beta",
)
class ReleasePrereleaseR8Tests(unittest.TestCase):
    def test_release_version_is_prerelease_4_8_0_beta(self):
        self.assertEqual(constants.RELEASE_VERSION, "4.8.0-beta")
        self.assertEqual(constants.LATEST_STABLE_RELEASE, "4.7.0")
        self.assertEqual(constants.ODPM_VERSION, constants.RELEASE_VERSION)

    def test_release_lines_documents_48_dev_line(self):
        text = (PROJECT_ROOT / "docs/contributing/release-lines.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("4.8.0-dev", text)
        self.assertIn("`4.8.0-beta`", text)
        self.assertIn("4.8.x", text)

    def test_rpm_spec_prerelease_release(self):
        spec = (PROJECT_ROOT / "packaging/odpm.spec").read_text(encoding="utf-8")
        self.assertIn("%global version 4.8.0", spec)
        self.assertIn("%global release beta", spec)

    def test_debian_changelog_prerelease_line(self):
        changelog = (PROJECT_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
        self.assertRegex(changelog, r"^odpm \(4\.8\.0~beta-1\)", re.MULTILINE)

    def test_release_notes_exist(self):
        notes = PROJECT_ROOT / ".github/release-notes/4.8.0-beta.md"
        self.assertTrue(notes.is_file(), msg=str(notes))
        text = notes.read_text(encoding="utf-8")
        self.assertIn("4.8.0-beta", text)
        self.assertIn("4.7.0", text)


if __name__ == "__main__":
    unittest.main()
