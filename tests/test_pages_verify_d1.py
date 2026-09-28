"""Contract tests for D1 ops/docs hygiene (Pages verify, legacy redirects)."""

from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class PagesVerifyD1Tests(unittest.TestCase):
    def test_verify_pages_deploy_script_exists(self):
        path = PROJECT_ROOT / "scripts" / "verify_pages_deploy.sh"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("versions.json", text)
        self.assertIn("--version", text)
        self.assertIn("ODPM_PAGES_VERIFY_RETRIES", text)

    def test_docs_workflow_verifies_pages_after_deploy(self):
        workflow = (PROJECT_ROOT / ".github/workflows/docs.yml").read_text(
            encoding="utf-8"
        )
        deploy_idx = workflow.index("actions/deploy-pages@v4")
        verify_job_idx = workflow.index("verify-pages:", deploy_idx)
        tail = workflow[verify_job_idx : verify_job_idx + 700]
        self.assertIn("verify_pages_deploy.sh", tail)
        self.assertIn("--version dev", tail)

    def test_release_packages_workflow_verifies_pages_after_deploy(self):
        workflow = (
            PROJECT_ROOT / ".github/workflows/release-packages.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("verify-pages:", workflow)
        self.assertIn("needs: publish-pages", workflow)
        verify_idx = workflow.index("verify-pages:")
        tail = workflow[verify_idx : verify_idx + 1200]
        self.assertIn('./repo/scripts/verify_pages_deploy.sh --version stable', tail)
        self.assertIn('./repo/scripts/verify_pages_deploy.sh --version "${VERSION}"', tail)
        self.assertNotIn("uses: actions/deploy-pages@v4", tail)

    def test_docs_workflow_splits_pages_verify_job(self):
        workflow = (PROJECT_ROOT / ".github/workflows/docs.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("verify-pages:", workflow)
        deploy_idx = workflow.index("actions/deploy-pages@v4")
        verify_job_idx = workflow.index("verify-pages:", deploy_idx)
        tail = workflow[verify_job_idx : verify_job_idx + 700]
        self.assertIn("--version dev", tail)
        self.assertNotIn("uses: actions/deploy-pages@v4", tail)

    def test_pages_artifact_from_gh_pages_script_exists(self):
        path = PROJECT_ROOT / "scripts" / "pages_artifact_from_gh_pages.sh"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("git archive", text)
        self.assertIn("versions.json", text)

    def test_release_lines_documents_pages_verify_runbook(self):
        text = (PROJECT_ROOT / "docs/contributing/release-lines.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("verify_pages_deploy.sh", text)
        self.assertIn("verify-pages", text)
        self.assertIn("OPS-01", text)

    def test_services_ru_is_deprecation_redirect(self):
        text = (
            PROJECT_ROOT / "dev_project/plugins/services_ru.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Устарело", text)
        self.assertNotIn("redis-stack-server", text)
        self.assertIn("plugins.md", text)

    def test_plugins_md_no_legacy_services_ru_blob_link(self):
        for rel in ("docs/reference/plugins.md", "docs/en/reference/plugins.md"):
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(plugins_doc=rel):
                self.assertNotIn("plugins/services_ru.md", text)
                self.assertNotIn("plugins/todo_ru.md", text)

    def test_i18n_doc_targets_46_dev_branch(self):
        text = (PROJECT_ROOT / "docs/contributing/i18n.md").read_text(encoding="utf-8")
        self.assertIn("`4.7.0-dev`", text)
        self.assertNotIn("`4.5-dev`", text)

    def test_en_manifest_migration_documents_service_patches(self):
        text = (
            PROJECT_ROOT / "docs/en/reference/manifest-migration.md"
        ).read_text(encoding="utf-8")
        self.assertIn("service_patches", text)
        self.assertIn("compose.patch", text)
        self.assertIn("adr-009-compose-service-patch", text)


if __name__ == "__main__":
    unittest.main()
