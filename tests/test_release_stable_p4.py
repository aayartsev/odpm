"""Contract tests for P4 stable 4.4.2 release prep."""

from __future__ import annotations

import unittest
from pathlib import Path

import dev_project.constants as constants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(
    constants.RELEASE_VERSION == "4.4.2",
    "P4 stable prep applies only when RELEASE_VERSION is 4.4.2",
)
class ReleaseStableP4Tests(unittest.TestCase):
    def test_release_version_is_stable_4_4_2(self):
        self.assertEqual(constants.RELEASE_VERSION, "4.4.2")
        self.assertEqual(constants.LATEST_STABLE_RELEASE, "4.4.2")
        self.assertEqual(constants.ODPM_VERSION, constants.RELEASE_VERSION)

    def test_stable_release_notes_exist_with_versioned_urls(self):
        notes = (PROJECT_ROOT / ".github" / "release-notes" / "4.4.2.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("/odpm/stable/", notes)
        self.assertNotIn("https://aayartsev.github.io/odpm/install/", notes)
        self.assertIn("pip install odpm", notes)
        self.assertIn("odpm_4.4.2-1_all.deb", notes)

    def test_install_readme_recommends_stable_4_4_2(self):
        for rel in ("docs/install/README.md", "docs/en/install/README.md"):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("4.4.2", text)
            self.assertIn("/odpm/stable/", text)

    def test_linux_deb_stable_expects_4_4_2(self):
        for rel in ("docs/install/linux-deb.md", "docs/en/install/linux-deb.md"):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("odpm version: 4.4.2", text)
            stable = text.index("### Stable")
            testing = text.index("### Pre-release")
            self.assertLess(stable, testing)

    def test_documentation_versions_stable_is_4_4_2(self):
        for rel in (
            "docs/getting-started/documentation-versions.md",
            "docs/en/getting-started/documentation-versions.md",
        ):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("**4.4.2**", text)
            self.assertIn("v4.4.2", text)

    def test_rpm_spec_stable_release(self):
        spec = (PROJECT_ROOT / "packaging" / "odpm.spec").read_text(encoding="utf-8")
        self.assertIn("%global version 4.4.2", spec)
        self.assertIn("%global release 1", spec)
        self.assertNotIn("%global release beta", spec)


if __name__ == "__main__":
    unittest.main()
