"""Contract tests for R6 stable 4.6.0 release prep."""

from __future__ import annotations

import unittest
from pathlib import Path

import dev_project.constants as constants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(
    constants.RELEASE_VERSION == "4.6.0",
    "R6 stable prep applies only when RELEASE_VERSION is 4.6.0",
)
class ReleaseStableR6Tests(unittest.TestCase):
    def test_release_version_is_stable_4_6_0(self):
        self.assertEqual(constants.RELEASE_VERSION, "4.6.0")
        self.assertEqual(constants.LATEST_STABLE_RELEASE, "4.6.0")
        self.assertEqual(constants.ODPM_VERSION, constants.RELEASE_VERSION)

    def test_stable_release_notes_exist_with_versioned_urls(self):
        notes = (PROJECT_ROOT / ".github" / "release-notes" / "4.6.0.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("/odpm/stable/", notes)
        self.assertNotIn("https://aayartsev.github.io/odpm/install/", notes)
        self.assertIn("pip install odpm", notes)
        self.assertIn("odpm_4.6.0-1_all.deb", notes)
        self.assertIn("odpm==4.6.0", notes)

    def test_install_readme_recommends_stable_4_6_0(self):
        for rel in ("docs/install/README.md", "docs/en/install/README.md"):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("4.6.0", text)
            self.assertIn("/odpm/stable/", text)

    def test_linux_deb_stable_expects_4_6_0(self):
        for rel in ("docs/install/linux-deb.md", "docs/en/install/linux-deb.md"):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("odpm version: 4.6.0", text)
            if rel.startswith("docs/install/"):
                stable = text.index("### Stable (рекомендуется")
                archived = text.index("### Предварительные версии")
            else:
                stable = text.index("### Stable (recommended")
                archived = text.index("### Pre-release")
            self.assertLess(stable, archived)

    def test_documentation_versions_stable_is_4_6_0(self):
        for rel in (
            "docs/getting-started/documentation-versions.md",
            "docs/en/getting-started/documentation-versions.md",
        ):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("**4.6.0**", text)
            self.assertIn("v4.6.0", text)

    def test_rpm_spec_stable_release(self):
        spec = (PROJECT_ROOT / "packaging" / "odpm.spec").read_text(encoding="utf-8")
        self.assertIn("%global version 4.6.0", spec)
        self.assertIn("%global release 1", spec)
        self.assertNotIn("%global release beta", spec)


if __name__ == "__main__":
    unittest.main()
