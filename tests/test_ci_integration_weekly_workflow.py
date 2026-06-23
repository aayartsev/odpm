"""CI Integration Weekly workflow contract (I2)."""

from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CiIntegrationWeeklyWorkflowTests(unittest.TestCase):
    def test_weekly_workflow_defines_i2_jobs(self):
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "ci-integration-weekly.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("fixture-golden-path:", workflow)
        self.assertIn("ci-image-build:", workflow)
        self.assertIn("deb-smoke:", workflow)
        self.assertIn("tests.integration.test_fixture_golden_path", workflow)
        self.assertIn("tests.integration.test_ci_image_build", workflow)
        self.assertIn("scripts/smoke_deb_install.sh", workflow)


if __name__ == "__main__":
    unittest.main()
