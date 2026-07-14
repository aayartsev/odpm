"""CI Docker workflow contract (ADR-006 integration gates)."""

from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CiDockerWorkflowContractTests(unittest.TestCase):
    def test_ci_docker_defines_mandatory_http_smoke_job(self):
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "ci-docker.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("http-smoke:", workflow)
        self.assertIn("needs: compose-smoke", workflow)
        self.assertIn("ODPM_RUN_HTTP_SMOKE", workflow)
        self.assertIn("tests.integration.test_http_smoke", workflow)
        self.assertIn("upload-artifact@v4", workflow)

    def test_ci_docker_compose_smoke_runs_plugin_and_hooks_e2e(self):
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "ci-docker.yml"
        ).read_text(encoding="utf-8")
        compose_block = workflow.split("compose-smoke:", 1)[1].split(
            "\n  http-smoke:", 1
        )[0]
        self.assertIn("ODPM_COMPOSE_SMOKE_PLUGIN", compose_block)
        self.assertIn("ODPM_COMPOSE_SMOKE_HOOKS", compose_block)
        self.assertIn("tests.integration.test_plugin_compose_e2e", compose_block)
        self.assertIn("tests.integration.test_hooks_integration_e2e", compose_block)

    def test_ci_docker_compose_smoke_stays_fast_gate(self):
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "ci-docker.yml"
        ).read_text(encoding="utf-8")
        compose_block = workflow.split("compose-smoke:", 1)[1].split(
            "\n  http-smoke:", 1
        )[0]
        self.assertIn("ODPM_RUN_DOCKER_COMPOSE_SMOKE", compose_block)
        self.assertIn("tests.integration.test_compose_smoke", compose_block)
        self.assertIn("timeout-minutes: 20", compose_block)

    def test_golden_path_remains_opt_in(self):
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "ci-docker.yml"
        ).read_text(encoding="utf-8")
        golden_block = workflow.split("golden-path:", 1)[1]
        self.assertIn("ODPM_GOLDEN_PATH_ENABLED", golden_block)
        self.assertIn("run-docker", golden_block)
        self.assertIn("needs: compose-smoke", golden_block)
        self.assertIn("timeout-minutes: 9", golden_block)
        self.assertIn('ODPM_GOLDEN_PATH_TIMEOUT: "60"', golden_block)


if __name__ == "__main__":
    unittest.main()
