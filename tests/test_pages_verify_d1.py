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
        verify_idx = workflow.index("verify_pages_deploy.sh", deploy_idx)
        self.assertIn("--version dev", workflow[verify_idx : verify_idx + 120])

    def test_release_packages_workflow_verifies_pages_after_deploy(self):
        workflow = (
            PROJECT_ROOT / ".github/workflows/release-packages.yml"
        ).read_text(encoding="utf-8")
        deploy_idx = workflow.rindex("actions/deploy-pages@v4")
        verify_idx = workflow.index("verify_pages_deploy.sh", deploy_idx)
        tail = workflow[verify_idx : verify_idx + 400]
        self.assertIn("--version stable", tail)
        self.assertIn('verify_pages_deploy.sh --version "${VERSION}"', tail)

    def test_release_lines_documents_pages_verify_runbook(self):
        text = (PROJECT_ROOT / "docs/contributing/release-lines.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("verify_pages_deploy.sh", text)
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

    def test_architecture_debt_has_46_track_section(self):
        text = (PROJECT_ROOT / "docs/contributing/architecture-debt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## 4.6 debt track (D1–D5)", text)
        self.assertIn("| **D1** | **DONE** |", text)
        self.assertIn("**1392**", text)

    def test_i18n_doc_targets_46_dev_branch(self):
        text = (PROJECT_ROOT / "docs/contributing/i18n.md").read_text(encoding="utf-8")
        self.assertIn("`4.6.0-dev`", text)
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
