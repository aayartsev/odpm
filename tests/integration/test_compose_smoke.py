"""Docker compose smoke: minimal fixture, odpm --skip-start, docker compose config."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.plan_smoke_helpers import repo_root

RUN_COMPOSE_SMOKE = os.environ.get("ODPM_RUN_DOCKER_COMPOSE_SMOKE") == "1"
ODPM_PY = Path(os.environ.get("ODPM_ODPM_PY", repo_root() / "odpm.py")).resolve()
SKIP_START_TIMEOUT = float(os.environ.get("ODPM_COMPOSE_SMOKE_TIMEOUT", "900"))


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _skip_reason() -> str | None:
    if not RUN_COMPOSE_SMOKE:
        return "set ODPM_RUN_DOCKER_COMPOSE_SMOKE=1"
    if not _docker_available():
        return "docker not available"
    if not ODPM_PY.is_file():
        return f"odpm entrypoint not found: {ODPM_PY}"
    return None


@unittest.skipIf(_skip_reason() is not None, _skip_reason() or "")
class ComposeSmokeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = provision_minimal_odpm_project(Path(self._tmp.name) / "project")
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _odpm_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self._home)
        env["PWD"] = str(self.project_dir)
        return env

    def test_skip_start_exits_zero_and_compose_config_valid(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ODPM_PY),
                "--skip-start",
                "--no-git-update",
            ],
            cwd=self.project_dir,
            env=self._odpm_env(),
            capture_output=True,
            text=True,
            timeout=SKIP_START_TIMEOUT,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=(result.stdout or "") + (result.stderr or ""),
        )
        compose_file = self.project_dir / "docker-compose.yml"
        self.assertTrue(compose_file.is_file(), "docker-compose.yml was not generated")
        self.assertGreater(compose_file.stat().st_size, 100)

        config_result = subprocess.run(
            ["docker", "compose", "config"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            config_result.returncode,
            0,
            msg=config_result.stderr or config_result.stdout,
        )
        self.assertIn("services:", config_result.stdout)


if __name__ == "__main__":
    unittest.main()
