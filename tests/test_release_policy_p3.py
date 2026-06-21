"""Contract tests for P3 maintainer release policy docs."""

from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ReleasePolicyP3Tests(unittest.TestCase):
    def test_release_lines_doc_exists_with_policy_sections(self):
        path = PROJECT_ROOT / "docs" / "contributing" / "release-lines.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        for needle in (
            "LATEST_STABLE_RELEASE",
            "Bootstrap docs versions",
            "Bootstrap Pages repos",
            "v4.4.2",
            "publish-pypi",
            "--merge",
            "mike",
        ):
            self.assertIn(needle, text, msg=needle)

    def test_packaging_doc_updated_for_merge_and_mike(self):
        path = PROJECT_ROOT / "docs" / "contributing" / "packaging.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("release-lines.md", text)
        self.assertIn("fetch_pages_repo.sh", text)
        self.assertIn("mike_pages_deploy.sh", text)
        self.assertIn("LATEST_STABLE_RELEASE", text)
        self.assertNotIn("preserve_pages_package_repos.sh", text)
        self.assertNotIn("ODPM_VERSION` | `4.0`", text)

    def test_packaging_pypi_on_tag_policy(self):
        text = (PROJECT_ROOT / "docs" / "contributing" / "packaging.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("publish-pypi", text)
        self.assertIn("TestPyPI", text)
        self.assertIn("production PyPI", text)

    def test_apt_readme_links_release_policy(self):
        text = (PROJECT_ROOT / "packaging" / "apt" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("release-lines.md", text)
        self.assertIn("v4.4.2", text)
        self.assertIn("--merge", text)

    def test_contributing_readme_links_release_lines(self):
        text = (PROJECT_ROOT / "docs" / "contributing" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("release-lines.md", text)

    def test_contributing_excluded_from_public_mkdocs(self):
        text = (PROJECT_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIn("contributing/**", text)


if __name__ == "__main__":
    unittest.main()
