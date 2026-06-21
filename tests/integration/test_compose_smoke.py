"""Docker compose smoke: minimal fixture, odpm --skip-start, docker compose config."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from dev_project.container_config import CONTAINER_CONFIG_SCHEMA_VERSION
from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_NAME
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.odpm_subprocess import run_odpm

RUN_COMPOSE_SMOKE = os.environ.get("ODPM_RUN_DOCKER_COMPOSE_SMOKE") == "1"
RUN_COMPOSE_SMOKE_MAILPIT = os.environ.get("ODPM_COMPOSE_SMOKE_MAILPIT") == "1"
SKIP_START_TIMEOUT = float(os.environ.get("ODPM_COMPOSE_SMOKE_TIMEOUT", "900"))


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _compose_smoke_skip_reason() -> str | None:
    if not RUN_COMPOSE_SMOKE:
        return "set ODPM_RUN_DOCKER_COMPOSE_SMOKE=1"
    if not _docker_available():
        return "docker not available"
    return None


def _mailpit_smoke_skip_reason() -> str | None:
    base = _compose_smoke_skip_reason()
    if base is not None:
        return base
    if not RUN_COMPOSE_SMOKE_MAILPIT:
        return "set ODPM_COMPOSE_SMOKE_MAILPIT=1"
    return None


class _ComposeSmokeTestCase(unittest.TestCase):
    manifest_v2_mailpit: bool = False

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = provision_minimal_odpm_project(
            Path(self._tmp.name) / "project",
            manifest_v2_mailpit=self.manifest_v2_mailpit,
        )
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_skip_start(self) -> subprocess.CompletedProcess[str]:
        return run_odpm(
            "--skip-start",
            "--no-git-update",
            cwd=self.project_dir,
            env={
                "HOME": str(self._home),
                "PWD": str(self.project_dir),
            },
            timeout=int(SKIP_START_TIMEOUT),
        )

    def _docker_compose_config(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "compose", "config"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )


@unittest.skipIf(_compose_smoke_skip_reason() is not None, _compose_smoke_skip_reason() or "")
class ComposeSmokeIntegrationTests(_ComposeSmokeTestCase):
    def test_skip_start_exits_zero_and_compose_config_valid(self) -> None:
        result = self._run_skip_start()
        self.assertEqual(
            result.returncode,
            0,
            msg=(result.stdout or "") + (result.stderr or ""),
        )

        compose_file = self.project_dir / "docker-compose.yml"
        self.assertTrue(compose_file.is_file(), "docker-compose.yml was not generated")
        compose_text = compose_file.read_text(encoding="utf-8")
        self.assertGreater(len(compose_text), 100)
        self.assertIn(constants.RUN_ODOO_ENTRYPOINT, compose_text)
        self.assertNotIn("{START_STRING}", compose_text)
        self.assertNotIn("main.py --config-base64-data", compose_text)

        runtime_config_path = (
            self.project_dir / constants.ODPM_RUNTIME_CONFIG_REL_PATH
        )
        self.assertTrue(runtime_config_path.is_file(), "runtime config.json missing")
        runtime_payload = json.loads(runtime_config_path.read_text(encoding="utf-8"))
        self.assertEqual(runtime_payload["schema_version"], CONTAINER_CONFIG_SCHEMA_VERSION)
        self.assertIn("venv_lock_hash", runtime_payload)

        config_result = self._docker_compose_config()
        self.assertEqual(
            config_result.returncode,
            0,
            msg=config_result.stderr or config_result.stdout,
        )
        config_text = config_result.stdout
        self.assertIn("services:", config_text)
        self.assertIn("odoo:", config_text)
        self.assertIn("db:", config_text)
        self.assertIn(constants.ODPM_CONFIG_PATH_ENV, config_text)

    def test_skip_start_is_idempotent_on_same_project_dir(self) -> None:
        first = self._run_skip_start()
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        second = self._run_skip_start()
        self.assertEqual(second.returncode, 0, msg=second.stderr)


@unittest.skipIf(_mailpit_smoke_skip_reason() is not None, _mailpit_smoke_skip_reason() or "")
class ComposeSmokeMailpitIntegrationTests(_ComposeSmokeTestCase):
    manifest_v2_mailpit = True

    def test_manifest_v2_mailpit_in_docker_compose_config(self) -> None:
        result = self._run_skip_start()
        self.assertEqual(
            result.returncode,
            0,
            msg=(result.stdout or "") + (result.stderr or ""),
        )

        compose_text = (self.project_dir / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn(f"  {MAILPIT_SERVICE_NAME}:", compose_text)
        self.assertIn("axllent/mailpit", compose_text)

        config_result = self._docker_compose_config()
        self.assertEqual(
            config_result.returncode,
            0,
            msg=config_result.stderr or config_result.stdout,
        )
        self.assertIn(f"{MAILPIT_SERVICE_NAME}:", config_result.stdout)
        self.assertIn("axllent/mailpit", config_result.stdout)


if __name__ == "__main__":
    unittest.main()
