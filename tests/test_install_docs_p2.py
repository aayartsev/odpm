"""Contract tests for P2 install docs (stable first, versioned URLs)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_LEGACY_DOC_URL = re.compile(
    r"https://aayartsev\.github\.io/odpm/"
    r"(?!stable/|4\.|dev/|apt/|yum/)"
)


class InstallDocsP2Tests(unittest.TestCase):
    def test_linux_deb_stable_section_before_testing_ru(self):
        text = (PROJECT_ROOT / "docs" / "install" / "linux-deb.md").read_text(
            encoding="utf-8"
        )
        stable = text.index("### Stable (рекомендуется")
        testing = text.index("### Pre-release")
        self.assertLess(stable, testing)
        self.assertIn("/odpm/apt stable main", text)
        self.assertIn("/stable/install/linux-deb/", text)

    def test_fedora_rpm_uses_pages_repo_files_en(self):
        text = (PROJECT_ROOT / "docs" / "en" / "install" / "fedora-rpm.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("https://aayartsev.github.io/odpm/yum/odpm-stable.repo", text)
        self.assertIn("https://aayartsev.github.io/odpm/yum/odpm-testing.repo", text)
        self.assertNotIn("raw.githubusercontent.com", text)

    def test_install_readme_links_stable_and_beta(self):
        for rel in ("docs/install/README.md", "docs/en/install/README.md"):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("4.4.2", text)
            self.assertIn("/odpm/stable/", text)
            self.assertIn("/4.4.3-beta/", text)
            self.assertIn("/4.4.2-beta/", text)
            self.assertIn("documentation-versions", text)

    def test_release_notes_use_versioned_doc_urls(self):
        notes_dir = PROJECT_ROOT / ".github" / "release-notes"
        for path in sorted(notes_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(release_notes=path.name):
                self.assertIsNone(
                    _LEGACY_DOC_URL.search(text),
                    msg=f"legacy flat docs URL in {path.name}",
                )
        beta = (notes_dir / "4.4.3-beta.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/stable/", beta)
        self.assertIn("/odpm/4.4.3-beta/", beta)
        archived = (notes_dir / "4.4.2-beta.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/4.4.2-beta/", archived)

    def test_finalize_publishes_yum_repo_templates(self):
        script = (PROJECT_ROOT / "scripts" / "mike_pages_finalize.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("odpm-stable.repo", script)
        self.assertIn("odpm-testing.repo", script)
        self.assertIn(".nojekyll", script)

    def test_pages_workflows_use_upload_pages_artifact_v5(self):
        for rel in (
            ".github/workflows/docs.yml",
            ".github/workflows/release-packages.yml",
            ".github/workflows/bootstrap-docs-versions.yml",
            ".github/workflows/bootstrap-pages-repos.yml",
        ):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(workflow=rel):
                self.assertIn("actions/upload-pages-artifact@v5", text)
                self.assertIn("include-hidden-files: true", text)

    def test_preserve_live_pages_repos_script_exists(self):
        path = PROJECT_ROOT / "scripts" / "preserve_live_pages_repos.sh"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("fetch_pages_repo.sh", text)


if __name__ == "__main__":
    unittest.main()
