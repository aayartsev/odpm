"""I2 fixture golden-path variant: in-repo minimal project + Odoo /web HTTP."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.integration.compose_golden_patch import (
    find_free_port,
    patch_compose_for_golden_path,
    postgres_service_name_from_compose,
)
from tests.integration.helpers import compose_service_logs, write_compose_debug_bundle
from tests.integration.http_wait import HttpWaitTimeoutError, wait_for_http_ok
from tests.odpm_subprocess import run_odpm

RUN_FIXTURE_GOLDEN = os.environ.get("ODPM_RUN_FIXTURE_GOLDEN_PATH") == "1"
FIXTURE_GOLDEN_TIMEOUT = float(os.environ.get("ODPM_FIXTURE_GOLDEN_TIMEOUT", "900"))
SKIP_START_TIMEOUT = float(os.environ.get("ODPM_COMPOSE_SMOKE_TIMEOUT", "900"))
DEBUG_BUNDLE_DIR = os.environ.get("ODPM_COMPOSE_DEBUG_DIR", "").strip()


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _fixture_golden_skip_reason() -> str | None:
    if not RUN_FIXTURE_GOLDEN:
        return "set ODPM_RUN_FIXTURE_GOLDEN_PATH=1"
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


@unittest.skipIf(
    _fixture_golden_skip_reason() is not None,
    _fixture_golden_skip_reason() or "",
)
class FixtureGoldenPathIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = provision_minimal_odpm_project(
            Path(self._tmp.name) / "project",
        )
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()
        self.compose_name = f"odpm-fixture-golden-{uuid.uuid4().hex[:12]}"
        self.odoo_host_port = find_free_port()

    def tearDown(self) -> None:
        if hasattr(self, "compose_argv"):
            subprocess.run(
                self.compose_argv + ["down"],
                cwd=self.project_dir,
                check=False,
                text=True,
            )
        self._tmp.cleanup()

    def test_fixture_compose_up_serves_odoo_web(self) -> None:
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

        compose_source = (self.project_dir / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        postgres_service = postgres_service_name_from_compose(compose_source)
        compose_dir = Path(self._tmp.name) / "compose"
        compose_dir.mkdir()
        compose_file = compose_dir / "docker-compose.yml"
        compose_file.write_text(
            patch_compose_for_golden_path(compose_source, self.odoo_host_port),
            encoding="utf-8",
        )
        self.compose_argv = _compose_argv(compose_file, self.compose_name)

        up = subprocess.run(
            self.compose_argv + ["up", "-d"],
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

        url = f"http://127.0.0.1:{self.odoo_host_port}/web"
        try:
            wait_for_http_ok(
                url,
                timeout=FIXTURE_GOLDEN_TIMEOUT,
                accept_status_codes={200, 303},
            )
        except HttpWaitTimeoutError as error:
            if DEBUG_BUNDLE_DIR:
                write_compose_debug_bundle(
                    Path(DEBUG_BUNDLE_DIR),
                    compose_argv=self.compose_argv,
                    project_dir=self.project_dir,
                    services=("odoo", postgres_service),
                )
            odoo_logs = compose_service_logs(
                self.compose_argv, self.project_dir, "odoo"
            )
            db_logs = compose_service_logs(
                self.compose_argv, self.project_dir, postgres_service, tail=20
            )
            raise AssertionError(
                f"{error}\n\n--- odoo logs (tail) ---\n{odoo_logs}\n\n"
                f"--- {postgres_service} logs (tail) ---\n{db_logs}"
            ) from error


if __name__ == "__main__":
    unittest.main()
