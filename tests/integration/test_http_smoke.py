"""Mandatory PR HTTP smoke: minimal fixture + Mailpit ``compose up`` + HTTP 200."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_NAME
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.integration.compose_golden_patch import find_free_port
from tests.integration.compose_http_smoke_patch import patch_mailpit_service_ports
from tests.integration.http_wait import HttpWaitTimeoutError, wait_for_http_ok
from tests.odpm_subprocess import run_odpm

RUN_HTTP_SMOKE = os.environ.get("ODPM_RUN_HTTP_SMOKE") == "1"
HTTP_SMOKE_TIMEOUT = float(os.environ.get("ODPM_HTTP_SMOKE_TIMEOUT", "600"))
SKIP_START_TIMEOUT = float(os.environ.get("ODPM_COMPOSE_SMOKE_TIMEOUT", "900"))


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _http_smoke_skip_reason() -> str | None:
    if not RUN_HTTP_SMOKE:
        return "set ODPM_RUN_HTTP_SMOKE=1"
    if not _docker_available():
        return "docker not available"
    return None


def _compose_argv(compose_file: Path, project_name: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "-p",
        project_name,
    ]


def _compose_service_logs(
    compose_argv: list[str], project_dir: Path, service: str, *, tail: int = 40
) -> str:
    result = subprocess.run(
        compose_argv + ["logs", "--no-color", "--tail", str(tail), service],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    return (result.stdout or result.stderr or "").strip()


@unittest.skipIf(_http_smoke_skip_reason() is not None, _http_smoke_skip_reason() or "")
class HttpSmokeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = provision_minimal_odpm_project(
            Path(self._tmp.name) / "project",
            manifest_v2_mailpit=True,
        )
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()
        self.compose_name = f"odpm-http-{uuid.uuid4().hex[:12]}"
        self.mailpit_ui_port = find_free_port()
        self.mailpit_smtp_port = find_free_port()

    def tearDown(self) -> None:
        if hasattr(self, "compose_argv"):
            subprocess.run(
                self.compose_argv + ["down"],
                cwd=self.project_dir,
                check=False,
                text=True,
            )
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

    def test_mailpit_compose_up_serves_http(self) -> None:
        skip_start = self._run_skip_start()
        self.assertEqual(
            skip_start.returncode,
            0,
            msg=(skip_start.stdout or "") + (skip_start.stderr or ""),
        )

        compose_source = (self.project_dir / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(f"  {MAILPIT_SERVICE_NAME}:", compose_source)

        compose_dir = Path(self._tmp.name) / "compose"
        compose_dir.mkdir()
        compose_file = compose_dir / "docker-compose.yml"
        compose_file.write_text(
            patch_mailpit_service_ports(
                compose_source,
                ui_port=self.mailpit_ui_port,
                smtp_port=self.mailpit_smtp_port,
                service_name=MAILPIT_SERVICE_NAME,
            ),
            encoding="utf-8",
        )
        self.compose_argv = _compose_argv(compose_file, self.compose_name)

        up = subprocess.run(
            self.compose_argv + ["up", "-d", MAILPIT_SERVICE_NAME],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )
        if up.returncode != 0:
            raise AssertionError(
                "docker compose up failed "
                f"(exit {up.returncode})\n\n"
                f"--- stdout ---\n{up.stdout}\n\n"
                f"--- stderr ---\n{up.stderr}"
            )

        url = f"http://127.0.0.1:{self.mailpit_ui_port}/"
        try:
            wait_for_http_ok(url, timeout=HTTP_SMOKE_TIMEOUT)
        except HttpWaitTimeoutError as error:
            logs = _compose_service_logs(
                self.compose_argv, self.project_dir, MAILPIT_SERVICE_NAME
            )
            raise AssertionError(
                f"{error}\n\n--- {MAILPIT_SERVICE_NAME} logs (tail) ---\n{logs}"
            ) from error


if __name__ == "__main__":
    unittest.main()
