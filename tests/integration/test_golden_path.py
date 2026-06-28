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
    postgres_service_name_from_compose,
)
from tests.integration.helpers import compose_service_logs, write_compose_debug_bundle
from tests.integration.http_wait import HttpWaitTimeoutError, wait_for_http_ok

RUN_DOCKER_INTEGRATION = os.environ.get("ODPM_RUN_DOCKER_INTEGRATION") == "1"
GOLDEN_PATH_PROJECT = os.environ.get("ODPM_GOLDEN_PATH_PROJECT", "").strip()
GOLDEN_PATH_TIMEOUT = float(os.environ.get("ODPM_GOLDEN_PATH_TIMEOUT", "90"))
DEBUG_BUNDLE_DIR = os.environ.get("ODPM_COMPOSE_DEBUG_DIR", "").strip()


def golden_path_maintenance_hint(*, odoo_logs: str, db_logs: str) -> str:
    """Actionable runner maintenance when golden-path logs match known stale-DB signatures."""
    combined = f"{odoo_logs}\n{db_logs}"
    hints: list[str] = []
    if "translate IS TRUE must be type boolean" in combined:
        hints.append(
            "PostgreSQL was created with an older Odoo major; recreate test_db "
            "or the postgres data volume, then run "
            "`odpm -d test_db -i base,web` on the runner."
        )
    if "_get_data" in odoo_logs and "res.lang" in odoo_logs:
        hints.append(
            "Odoo web templates expect Odoo 19+ ORM but the database or addons "
            "are inconsistent — usually fixed by the same DB recreate as above."
        )
    if not hints:
        return ""
    return (
        "Runner maintenance (see docs/contributing/ci.md):\n- "
        + "\n- ".join(hints)
    )


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
    return compose_service_logs(compose_argv, project_dir, service, tail=tail)


@unittest.skipIf(
    _golden_path_skip_reason() is not None,
    _golden_path_skip_reason() or "",
)
class GoldenPathIntegrationTests(unittest.TestCase):
    project_dir: Path
    compose_name: str
    compose_argv: list[str]
    odoo_host_port: int
    postgres_service: str
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
        cls.postgres_service = postgres_service_name_from_compose(source)
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
            wait_for_http_ok(url, timeout=GOLDEN_PATH_TIMEOUT)
        except HttpWaitTimeoutError as error:
            if DEBUG_BUNDLE_DIR:
                write_compose_debug_bundle(
                    Path(DEBUG_BUNDLE_DIR),
                    compose_argv=self.compose_argv,
                    project_dir=self.project_dir,
                    services=("odoo", self.postgres_service),
                )
            odoo_logs = _compose_service_logs(
                self.compose_argv, self.project_dir, "odoo"
            )
            db_logs = _compose_service_logs(
                self.compose_argv,
                self.project_dir,
                self.postgres_service,
                tail=15,
            )
            hint = golden_path_maintenance_hint(odoo_logs=odoo_logs, db_logs=db_logs)
            hint_block = f"\n\n--- maintenance ---\n{hint}" if hint else ""
            raise AssertionError(
                f"{error}\n\n--- odoo logs (tail) ---\n{odoo_logs}\n\n"
                f"--- {self.postgres_service} logs (tail) ---\n{db_logs}"
                f"{hint_block}"
            ) from error


if __name__ == "__main__":
    unittest.main()


class GoldenPathMaintenanceHintTests(unittest.TestCase):
    def test_hint_for_stale_postgres_schema(self) -> None:
        hint = golden_path_maintenance_hint(
            odoo_logs="QWebException res.lang _get_data",
            db_logs="translate IS TRUE must be type boolean",
        )
        self.assertIn("recreate test_db", hint)
        self.assertIn("Odoo 19", hint)

    def test_hint_empty_for_unrelated_logs(self) -> None:
        self.assertEqual(
            golden_path_maintenance_hint(odoo_logs="ok", db_logs="ok"),
            "",
        )


class GoldenPathMaintenanceScriptsTests(unittest.TestCase):
    def test_refresh_and_preflight_scripts_exist(self) -> None:
        root = Path(__file__).resolve().parents[2]
        for name in (
            "golden_path_project_lib.sh",
            "refresh_golden_path_project.sh",
            "preflight_golden_path_project.sh",
        ):
            path = root / "scripts" / name
            self.assertTrue(path.is_file(), msg=name)
            self.assertTrue(path.stat().st_mode & 0o111, msg=name)
        refresh = (root / "scripts" / "refresh_golden_path_project.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("ODPM_GOLDEN_PATH_AUTO_REMEDIATE", refresh)
        self.assertIn("golden_path_remediate_database", refresh)
        lib = (root / "scripts" / "golden_path_project_lib.sh").read_text(encoding="utf-8")
        self.assertIn("--db-drop", lib)
