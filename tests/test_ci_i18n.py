"""CI i18n gate and catalog tooling contract tests (Phase L)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CiI18nWorkflowTests(unittest.TestCase):
    def test_ci_yml_defines_i18n_job(self):
        workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("i18n:", workflow)
        self.assertIn("check_i18n_catalog.py", workflow)
        self.assertIn("audit_user_strings.py", workflow)


class CheckI18nCatalogTests(unittest.TestCase):
    def test_check_i18n_catalog_passes(self):
        result = subprocess.run(
            ["python3", "scripts/check_i18n_catalog.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=(result.stdout or "") + (result.stderr or ""),
        )
        self.assertIn("ru_RU and en_US", result.stdout)


class AuditUserStringsTests(unittest.TestCase):
    def test_audit_user_strings_runs(self):
        result = subprocess.run(
            ["python3", "scripts/audit_user_strings.py", "--summary"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("audit_user_strings summary", result.stdout)


if __name__ == "__main__":
    unittest.main()
