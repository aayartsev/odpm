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
    def test_linux_deb_stable_section_before_archived_ru(self):
        text = (PROJECT_ROOT / "docs" / "install" / "linux-deb.md").read_text(
            encoding="utf-8"
        )
        stable = text.index("### Stable (рекомендуется")
        archived = text.index("### Предварительные версии (архив)")
        self.assertLess(stable, archived)
        self.assertIn("/odpm/apt stable main", text)
        self.assertIn("/stable/install/linux-deb/", text)
        self.assertIn("odpm version: 4.6.0", text)

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
            self.assertIn("4.6.0", text)
            self.assertIn("/odpm/stable/", text)
            self.assertIn("/4.6.0-beta/", text)
            if rel.startswith("docs/install/"):
                self.assertIn("/odpm/dev/install/", text)
            self.assertIn("/4.5.0-beta/", text)
            self.assertIn("/4.4.3-beta/", text)
            self.assertIn("/4.4.2-beta/", text)
            self.assertIn("documentation-versions", text)

    def test_linux_deb_and_fedora_mention_archived_46_beta(self):
        cases = (
            "docs/install/linux-deb.md",
            "docs/install/fedora-rpm.md",
            "docs/en/install/linux-deb.md",
            "docs/en/install/fedora-rpm.md",
        )
        for rel in cases:
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(doc=rel):
                self.assertIn("4.6.0", text)
                self.assertIn("odpm version: 4.6.0", text)
                self.assertIn("4.6.0-beta", text)
                self.assertIn("/4.6.0-beta/", text)

    def test_release_notes_use_versioned_doc_urls(self):
        notes_dir = PROJECT_ROOT / ".github" / "release-notes"
        for path in sorted(notes_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(release_notes=path.name):
                self.assertIsNone(
                    _LEGACY_DOC_URL.search(text),
                    msg=f"legacy flat docs URL in {path.name}",
                )
        stable = (notes_dir / "4.4.3.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/stable/", stable)
        stable45 = (notes_dir / "4.5.0.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/stable/", stable45)
        self.assertIn("odpm_4.5.0-1_all.deb", stable45)
        beta = (notes_dir / "4.4.3-beta.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/stable/", beta)
        self.assertIn("/odpm/4.4.3-beta/", beta)
        beta45 = (notes_dir / "4.5.0-beta.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/stable/", beta45)
        self.assertIn("/odpm/4.5.0-beta/", beta45)
        archived = (notes_dir / "4.4.2-beta.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/4.4.2-beta/", archived)
        beta46 = (notes_dir / "4.6.0-beta.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/stable/", beta46)
        self.assertIn("/odpm/4.6.0-beta/", beta46)
        self.assertIn("odpm_4.6.0~beta-1_all.deb", beta46)
        self.assertIn("odpm-4.6.0-beta.fc", beta46)
        self.assertIn("odpm==4.6.0-beta", beta46)
        self.assertIn("github.com/aayartsev/odpm/blob/v4.6.0-beta/CHANGELOG.md", beta46)
        self.assertIn("/4.6.0-beta/install/linux-deb/", beta46)
        self.assertIn("/4.6.0-beta/en/install/linux-deb/", beta46)
        self.assertIn("/4.6.0-beta/install/fedora-rpm/", beta46)
        self.assertIn("/4.6.0-beta/en/install/fedora-rpm/", beta46)
        self.assertIn("/4.6.0-beta/install/", beta46)
        self.assertIn("/4.6.0-beta/en/install/", beta46)
        stable46 = (notes_dir / "4.6.0.md").read_text(encoding="utf-8")
        self.assertIn("/odpm/stable/", stable46)
        self.assertIn("odpm_4.6.0-1_all.deb", stable46)
        self.assertIn("odpm-4.6.0.fc", stable46)
        self.assertIn("odpm==4.6.0", stable46)
        self.assertIn("github.com/aayartsev/odpm/blob/v4.6.0/CHANGELOG.md", stable46)
        self.assertIn("/4.6.0-beta/en/install/", stable46)
        self.assertIn("/4.6.0-beta/install/", stable46)

    def test_mkdocs_edit_uri_targets_active_dev_branch(self):
        text = (PROJECT_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIn("edit_uri: edit/4.6.0-dev/docs/", text)

    def test_ci_workflows_target_46_dev_branch(self):
        for rel in (
            ".github/workflows/ci.yml",
            ".github/workflows/ci-docker.yml",
            ".github/workflows/docs.yml",
        ):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(workflow=rel):
                self.assertIn("4.6.0-dev", text)

    def test_ci_yml_defines_i18n_job(self):
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("i18n:", workflow)
        self.assertIn("check_i18n_catalog.py", workflow)

    def test_finalize_publishes_yum_repo_templates(self):
        script = (PROJECT_ROOT / "scripts" / "mike_pages_finalize.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("odpm-stable.repo", script)
        self.assertIn("odpm-testing.repo", script)
        self.assertIn(".nojekyll", script)
        self.assertIn("fix_stable_version_picker_symlinks", script)

    def test_public_docs_do_not_link_to_excluded_contributing_paths(self):
        """contributing/** is excluded from MkDocs; relative links 404 on Pages."""
        rel_contrib = re.compile(
            r"\[[^\]]*\]\((?:\.\./)+contributing/[^)]+\)"
        )
        abs_contrib = re.compile(
            r"\[[^\]]*\]\(contributing/[^h][^)]*\)"
        )
        roots = (
            PROJECT_ROOT / "docs" / "reference",
            PROJECT_ROOT / "docs" / "scenarios",
            PROJECT_ROOT / "docs" / "install",
            PROJECT_ROOT / "docs" / "getting-started",
            PROJECT_ROOT / "docs" / "operations",
            PROJECT_ROOT / "docs" / "en",
            PROJECT_ROOT / "docs",
        )
        checked: set[Path] = set()
        for root in roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*.md")):
                if path in checked:
                    continue
                rel = path.relative_to(PROJECT_ROOT).as_posix()
                if rel.startswith("docs/contributing/"):
                    continue
                if rel.startswith("docs/how-to/") or rel.startswith("docs/changelog-prep/"):
                    continue
                if path.name.startswith("smoke-") or path.name == "cross-cutting-debt-plan.md":
                    continue
                checked.add(path)
                text = path.read_text(encoding="utf-8")
                with self.subTest(doc=rel):
                    self.assertIsNone(
                        rel_contrib.search(text),
                        msg=f"relative contributing link in {rel}",
                    )
                    self.assertIsNone(
                        abs_contrib.search(text),
                        msg=f"absolute contributing link in {rel}",
                    )

    def test_pages_workflows_use_upload_pages_artifact_v5(self):
        for rel in (
            ".github/workflows/docs.yml",
            ".github/workflows/release-packages.yml",
            ".github/workflows/bootstrap-docs-versions.yml",
            ".github/workflows/bootstrap-pages-repos.yml",
            ".github/workflows/redeploy-pages.yml",
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
