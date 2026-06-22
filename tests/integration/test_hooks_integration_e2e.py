"""I2 hooks E2E: manifest shell hooks + local Python hook runner in docker job."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.fixtures.local_plugins.hooks_e2e import MARKER_REL_PATH, PLUGIN_ID
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.odpm_subprocess import run_odpm

RUN_COMPOSE_SMOKE = os.environ.get("ODPM_RUN_DOCKER_COMPOSE_SMOKE") == "1"
RUN_HOOKS_E2E = os.environ.get("ODPM_COMPOSE_SMOKE_HOOKS") == "1"
SKIP_START_TIMEOUT = float(os.environ.get("ODPM_COMPOSE_SMOKE_TIMEOUT", "900"))
SHELL_HOOK_MARKER = ".odpm/shell-hook.ok"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _hooks_e2e_skip_reason() -> str | None:
    if not RUN_COMPOSE_SMOKE:
        return "set ODPM_RUN_DOCKER_COMPOSE_SMOKE=1"
    if not RUN_HOOKS_E2E:
        return "set ODPM_COMPOSE_SMOKE_HOOKS=1"
    if not _docker_available():
        return "docker not available"
    return None


@unittest.skipIf(_hooks_e2e_skip_reason() is not None, _hooks_e2e_skip_reason() or "")
class ComposeSmokeHooksIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = provision_minimal_odpm_project(
            Path(self._tmp.name) / "project",
            manifest_v2_mailpit=True,
            manifest_hooks={
                "post_prepare": [
                    ["touch", SHELL_HOOK_MARKER],
                    PLUGIN_ID,
                ],
            },
            manifest_extensions={"local": ["hooks_e2e"]},
            local_plugins=("hooks_e2e",),
        )
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_skip_start_runs_shell_and_python_post_prepare_hooks(self) -> None:
        result = run_odpm(
            "--skip-start",
            "--no-git-update",
            cwd=self.project_dir,
            env={"HOME": str(self._home), "PWD": str(self.project_dir)},
            timeout=int(SKIP_START_TIMEOUT),
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=(result.stdout or "") + (result.stderr or ""),
        )
        self.assertTrue(
            (self.project_dir / SHELL_HOOK_MARKER).is_file(),
            "shell manifest hook did not create marker file",
        )
        self.assertTrue(
            (self.project_dir / MARKER_REL_PATH).is_file(),
            "local Python hook runner did not create marker file",
        )


if __name__ == "__main__":
    unittest.main()
