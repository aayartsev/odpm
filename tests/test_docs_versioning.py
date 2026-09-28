"""Contract tests for mike-based docs versioning (P1)."""

from __future__ import annotations

import unittest
from pathlib import Path

import dev_project.constants as constants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DocsVersioningTests(unittest.TestCase):
    def test_mkdocs_configures_mike_provider(self):
        text = (PROJECT_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        self.assertIn("site_url: https://aayartsev.github.io/odpm/stable/", text)
        self.assertIn("provider: mike", text)
        self.assertIn("default: stable", text)
        self.assertIn("custom_dir: docs/overrides", text)

    def test_requirements_include_mike(self):
        reqs = (PROJECT_ROOT / "requirements-docs.txt").read_text(encoding="utf-8")
        self.assertRegex(reqs, r"(?m)^mike>=")

    def test_mike_scripts_exist_and_executable(self):
        for name in (
            "mike_pages_deploy.sh",
            "mike_pages_finalize.sh",
            "pages_artifact_from_gh_pages.sh",
        ):
            script = PROJECT_ROOT / "scripts" / name
            self.assertTrue(script.is_file(), msg=name)
            self.assertTrue(script.stat().st_mode & 0o111, msg=name)

    def test_documentation_versions_hub_pages_exist(self):
        for rel in (
            "docs/getting-started/documentation-versions.md",
            "docs/en/getting-started/documentation-versions.md",
        ):
            path = PROJECT_ROOT / rel
            self.assertTrue(path.is_file(), msg=rel)
            self.assertIn("stable", path.read_text(encoding="utf-8").lower())

    def test_version_banner_override_exists(self):
        banner = PROJECT_ROOT / "docs" / "overrides" / "main.html"
        self.assertTrue(banner.is_file())
        self.assertIn("stable", banner.read_text(encoding="utf-8"))

    def test_latest_stable_release_constant(self):
        self.assertEqual(constants.LATEST_STABLE_RELEASE, "4.6.0")
        if "-" not in constants.RELEASE_VERSION:
            self.assertEqual(constants.LATEST_STABLE_RELEASE, constants.RELEASE_VERSION)

    def test_bootstrap_prepare_scripts_exist(self):
        for name in ("prepare_bootstrap_docs.sh", "patch_mkdocs_bootstrap.py"):
            path = PROJECT_ROOT / "scripts" / name
            self.assertTrue(path.is_file(), msg=name)
            if name.endswith(".sh"):
                self.assertTrue(path.stat().st_mode & 0o111, msg=name)

    def test_bootstrap_workflow_uses_prepare_script(self):
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "bootstrap-docs-versions.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("prepare_bootstrap_docs.sh", workflow)
        self.assertNotIn('checkout "${{ inputs.tag }}" -- docs/', workflow)

    def test_docs_workflow_uses_mike(self):
        workflow = (PROJECT_ROOT / ".github" / "workflows" / "docs.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("mike_pages_deploy.sh", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("fetch-depth: 0", workflow)


if __name__ == "__main__":
    unittest.main()
