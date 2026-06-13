"""Opt-in golden-path E2E: docker compose up + host-side HTTP 200 on /web."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from tests.integration.compose_golden_patch import (
    find_free_port,
    patch_compose_for_golden_path,
)
from tests.integration.http_wait import HttpWaitTimeoutError, wait_for_http_ok

RUN_DOCKER_INTEGRATION = os.environ.get("ODPM_RUN_DOCKER_INTEGRATION") == "1"
GOLDEN_PATH_PROJECT = os.environ.get("ODPM_GOLDEN_PATH_PROJECT", "").strip()
GOLDEN_PATH_TIMEOUT = float(os.environ.get("ODPM_GOLDEN_PATH_TIMEOUT", "300"))


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _golden_path_skip_reason() -> str | None:
    if not RUN_DOCKER_INTEGRATION:
        return "set ODPM_RUN_DOCKER_INTEGRATION=1"
    if not GOLDEN_PATH_PROJECT:
        return "set ODPM_GOLDEN_PATH_PROJECT=/path/to/initialized/odpm/project"
    project_dir = Path(GOLDEN_PATH_PROJECT)
    if not project_dir.is_dir():
        return f"ODPM_GOLDEN_PATH_PROJECT is not a directory: {project_dir}"
    compose_file = project_dir / "docker-compose.yml"
    if not compose_file.is_file():
        return f"missing docker-compose.yml in {project_dir}"
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


def _default_project_stack_running(project_dir: Path) -> bool:
    result = subprocess.run(
        ["docker", "compose", "ps", "-q"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


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


@unittest.skipIf(
    _golden_path_skip_reason() is not None,
    _golden_path_skip_reason() or "",
)
class GoldenPathIntegrationTests(unittest.TestCase):
    project_dir: Path
    compose_name: str
    compose_argv: list[str]
    odoo_host_port: int
    _compose_tempdir: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_dir = Path(GOLDEN_PATH_PROJECT).resolve()
        if _default_project_stack_running(cls.project_dir):
            raise unittest.SkipTest(
                "Project compose stack is already running. Run "
                "`docker compose down` in the project directory first "
                "(Postgres data directory cannot be used by two containers)."
            )
        cls.compose_name = f"odpm-golden-{uuid.uuid4().hex[:12]}"
        cls.odoo_host_port = find_free_port()
        source = (cls.project_dir / "docker-compose.yml").read_text(encoding="utf-8")
        cls._compose_tempdir = tempfile.TemporaryDirectory(prefix="odpm-golden-compose-")
        compose_file = Path(cls._compose_tempdir.name) / "docker-compose.yml"
        compose_file.write_text(
            patch_compose_for_golden_path(source, cls.odoo_host_port),
            encoding="utf-8",
        )
        cls.compose_argv = _compose_argv(compose_file, cls.compose_name)

    @classmethod
    def tearDownClass(cls) -> None:
        subprocess.run(
            cls.compose_argv + ["down"],
            cwd=cls.project_dir,
            check=False,
            text=True,
        )
        cls._compose_tempdir.cleanup()

    def test_compose_up_serves_web(self) -> None:
        subprocess.run(
            self.compose_argv + ["up", "-d"],
            cwd=self.project_dir,
            check=True,
            text=True,
        )
        url = f"http://127.0.0.1:{self.odoo_host_port}/web"
        try:
            wait_for_http_ok(url, timeout=GOLDEN_PATH_TIMEOUT)
        except HttpWaitTimeoutError as error:
            odoo_logs = _compose_service_logs(
                self.compose_argv, self.project_dir, "odoo"
            )
            db_logs = _compose_service_logs(
                self.compose_argv, self.project_dir, "db", tail=15
            )
            raise AssertionError(
                f"{error}\n\n--- odoo logs (tail) ---\n{odoo_logs}\n\n"
                f"--- db logs (tail) ---\n{db_logs}"
            ) from error


if __name__ == "__main__":
    unittest.main()
