"""I2 plugin E2E: sample_plugin entry points + manifest v2 Mailpit compose."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_NAME
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.fixtures.sample_plugin import sample_odpm_plugin
from tests.odpm_subprocess import run_odpm

RUN_COMPOSE_SMOKE = os.environ.get("ODPM_RUN_DOCKER_COMPOSE_SMOKE") == "1"
RUN_PLUGIN_E2E = os.environ.get("ODPM_COMPOSE_SMOKE_PLUGIN") == "1"
SKIP_START_TIMEOUT = float(os.environ.get("ODPM_COMPOSE_SMOKE_TIMEOUT", "900"))
SAMPLE_PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "sample_plugin"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _plugin_e2e_skip_reason() -> str | None:
    if not RUN_COMPOSE_SMOKE:
        return "set ODPM_RUN_DOCKER_COMPOSE_SMOKE=1"
    if not RUN_PLUGIN_E2E:
        return "set ODPM_COMPOSE_SMOKE_PLUGIN=1"
    if not _docker_available():
        return "docker not available"
    return None


def _ensure_sample_plugin_installed() -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(SAMPLE_PLUGIN_ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )


@unittest.skipIf(_plugin_e2e_skip_reason() is not None, _plugin_e2e_skip_reason() or "")
class ComposeSmokePluginIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        _ensure_sample_plugin_installed()
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = provision_minimal_odpm_project(
            Path(self._tmp.name) / "project",
            manifest_v2_mailpit=True,
        )
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_sample_plugin_prepare_step_in_plan_after_skip_start(self) -> None:
        skip_start = run_odpm(
            "--skip-start",
            "--no-git-update",
            cwd=self.project_dir,
            env={"HOME": str(self._home), "PWD": str(self.project_dir)},
            timeout=int(SKIP_START_TIMEOUT),
        )
        self.assertEqual(
            skip_start.returncode,
            0,
            msg=(skip_start.stdout or "") + (skip_start.stderr or ""),
        )

        plan = run_odpm(
            "plan",
            cwd=self.project_dir,
            env={"HOME": str(self._home), "PWD": str(self.project_dir)},
            timeout=120,
        )
        self.assertEqual(plan.returncode, 0, msg=plan.stderr or plan.stdout)
        combined = (plan.stdout or "") + (plan.stderr or "")
        self.assertIn(sample_odpm_plugin.SAMPLE_PREPARE_STEP_ID, combined)

        compose_text = (self.project_dir / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(f"  {MAILPIT_SERVICE_NAME}:", compose_text)

        config = subprocess.run(
            ["docker", "compose", "config"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(config.returncode, 0, msg=config.stderr or config.stdout)
        self.assertIn(MAILPIT_SERVICE_NAME, config.stdout)


if __name__ == "__main__":
    unittest.main()
