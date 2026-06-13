"""Opt-in E2E: every Odoo ``--dev`` flag via user_settings.json → compose → live HTTP."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

from tests.integration.compose_golden_patch import (
    find_free_port,
    patch_compose_for_golden_path,
)
from tests.integration.dev_mode_probe import (
    DEV_MODE_COMPOSE_CASES,
    container_restart_count,
    dev_flag_from_compose_command,
    expected_http_status_codes,
    extract_odoo_compose_command,
    patch_user_settings_dev_mode,
)
from tests.integration.dev_mode_reload_probe import (
    resolve_probe_python_file,
    run_autoreload_probe,
)
from tests.integration.http_wait import HttpWaitTimeoutError, wait_for_http_ok

from dev_project import constants

RUN_DOCKER_INTEGRATION = os.environ.get("ODPM_RUN_DOCKER_INTEGRATION") == "1"
GOLDEN_PATH_PROJECT = os.environ.get("ODPM_GOLDEN_PATH_PROJECT", "").strip()
DEV_MODE_TIMEOUT = float(os.environ.get("ODPM_DEV_MODE_TIMEOUT", "240"))
DEV_MODE_RELOAD_TIMEOUT = float(os.environ.get("ODPM_DEV_MODE_RELOAD_TIMEOUT", "90"))
REPO_ROOT = Path(__file__).resolve().parents[2]
ODPM_PY = Path(os.environ.get("ODPM_ODPM_PY", REPO_ROOT / "odpm.py")).resolve()


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _skip_reason(*, require_docker: bool = True) -> str | None:
    if not RUN_DOCKER_INTEGRATION:
        return "set ODPM_RUN_DOCKER_INTEGRATION=1"
    if not GOLDEN_PATH_PROJECT:
        return "set ODPM_GOLDEN_PATH_PROJECT=/path/to/initialized/odpm/project"
    project_dir = Path(GOLDEN_PATH_PROJECT)
    if not project_dir.is_dir():
        return f"ODPM_GOLDEN_PATH_PROJECT is not a directory: {project_dir}"
    if not (project_dir / "docker-compose.yml").is_file():
        return f"missing docker-compose.yml in {project_dir}"
    if not (project_dir / "user_settings.json").is_file():
        return f"missing user_settings.json in {project_dir}"
    if not ODPM_PY.is_file():
        return f"odpm entrypoint not found: {ODPM_PY}"
    if require_docker and not _docker_available():
        return "docker not available"
    return None


def _project_stack_running(project_dir: Path) -> bool:
    result = subprocess.run(
        ["docker", "compose", "ps", "-q"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


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


class _DevModeProjectTestBase(unittest.TestCase):
    project_dir: Path
    user_settings_path: Path
    user_settings_backup: str
    odpm_py: Path

    @classmethod
    def setUpClass(cls) -> None:
        reason = _skip_reason(require_docker=False)
        if reason is not None:
            raise unittest.SkipTest(reason)
        cls.project_dir = Path(GOLDEN_PATH_PROJECT).resolve()
        cls.user_settings_path = cls.project_dir / "user_settings.json"
        cls.user_settings_backup = cls.user_settings_path.read_text(encoding="utf-8")
        cls.odpm_py = ODPM_PY

    @classmethod
    def tearDownClass(cls) -> None:
        cls.user_settings_path.write_text(cls.user_settings_backup, encoding="utf-8")

    def _odpm_subprocess_env(self) -> dict[str, str]:
        # OdpmPipeline resolves start_dir as PWD before getcwd(); align with cwd.
        env = os.environ.copy()
        env["PWD"] = str(self.project_dir)
        return env

    def _run_odpm_skip_start(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.odpm_py), "--skip-start"],
            cwd=self.project_dir,
            env=self._odpm_subprocess_env(),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise AssertionError(
                "odpm --skip-start failed "
                f"(exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
            )

    def _assert_compose_dev_flag(
        self,
        case_id: str,
        expected_dev_argv: str | None,
    ) -> None:
        compose_source = (self.project_dir / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        command = extract_odoo_compose_command(compose_source)
        actual_dev = dev_flag_from_compose_command(command)
        self.assertEqual(
            actual_dev,
            expected_dev_argv,
            msg=f"compose --dev mismatch for case {case_id}",
        )


@unittest.skipIf(_skip_reason(require_docker=False) is not None, _skip_reason(require_docker=False) or "")
class DevModeComposeIntegrationTests(_DevModeProjectTestBase):
    """Regenerate compose for every dev_mode value on a real project (no stack restart)."""

    def test_all_dev_mode_flags_compose(self) -> None:
        for case_id, dev_mode_value, expected_argv in DEV_MODE_COMPOSE_CASES:
            with self.subTest(case_id=case_id, dev_mode=dev_mode_value):
                patch_user_settings_dev_mode(self.user_settings_path, dev_mode_value)
                self._run_odpm_skip_start()
                self._assert_compose_dev_flag(case_id, expected_argv)


@unittest.skipIf(_skip_reason(require_docker=True) is not None, _skip_reason(require_docker=True) or "")
class DevModeLiveIntegrationTests(_DevModeProjectTestBase):
    """Bring up an isolated compose stack per dev_mode case (requires project stack down)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if _project_stack_running(cls.project_dir):
            raise unittest.SkipTest(
                "Project compose stack is already running. Run "
                "`docker compose down` in the project directory first "
                "(Postgres data directory cannot be used by two containers)."
            )

    def _run_live_case(
        self,
        case_id: str,
        dev_mode_value: object,
        expected_dev_argv: str | None,
    ) -> None:
        patch_user_settings_dev_mode(self.user_settings_path, dev_mode_value)
        self._run_odpm_skip_start()
        self._assert_compose_dev_flag(case_id, expected_dev_argv)

        compose_source = (self.project_dir / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        odoo_host_port = find_free_port()
        compose_name = f"odpm-devmode-{case_id}-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory(prefix="odpm-devmode-compose-") as tmp:
            compose_file = Path(tmp) / "docker-compose.yml"
            compose_file.write_text(
                patch_compose_for_golden_path(compose_source, odoo_host_port),
                encoding="utf-8",
            )
            compose_argv = _compose_argv(compose_file, compose_name)

            subprocess.run(
                compose_argv + ["up", "-d"],
                cwd=self.project_dir,
                check=True,
                text=True,
            )
            try:
                url = f"http://127.0.0.1:{odoo_host_port}/web/login"
                try:
                    status = wait_for_http_ok(
                        url,
                        timeout=DEV_MODE_TIMEOUT,
                        accept_status_codes=expected_http_status_codes(dev_mode_value),
                    )
                except HttpWaitTimeoutError as error:
                    odoo_logs = _compose_service_logs(
                        compose_argv, self.project_dir, "odoo"
                    )
                    raise AssertionError(
                        f"{error}\n\n--- odoo logs (tail) ---\n{odoo_logs}"
                    ) from error

                restarts = container_restart_count(
                    compose_argv, self.project_dir, "odoo"
                )
                self.assertGreaterEqual(
                    restarts,
                    0,
                    msg="could not read odoo container RestartCount",
                )
                self.assertEqual(
                    restarts,
                    0,
                    msg=(
                        f"odoo container restarted during case {case_id} "
                        f"(dev_mode={dev_mode_value!r}, HTTP={status})"
                    ),
                )
            finally:
                subprocess.run(
                    compose_argv + ["down"],
                    cwd=self.project_dir,
                    check=False,
                    text=True,
                )

    def test_all_dev_mode_flags_live(self) -> None:
        for case_id, dev_mode_value, expected_argv in DEV_MODE_COMPOSE_CASES:
            with self.subTest(case_id=case_id, dev_mode=dev_mode_value):
                self._run_live_case(case_id, dev_mode_value, expected_argv)


@unittest.skipIf(_skip_reason(require_docker=True) is not None, _skip_reason(require_docker=True) or "")
class DevModeAutoreloadIntegrationTests(_DevModeProjectTestBase):
    """Save a developing-project ``.py`` file with ``dev_mode=all`` and expect autoreload."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if _project_stack_running(cls.project_dir):
            raise unittest.SkipTest(
                "Project compose stack is already running. Run "
                "`docker compose down` in the project directory first."
            )

    def test_dev_mode_all_triggers_python_autoreload_on_save(self) -> None:
        dev_mode_value = constants.ODOO_DEV_MODE_ALL
        patch_user_settings_dev_mode(self.user_settings_path, dev_mode_value)
        self._run_odpm_skip_start()
        self._assert_compose_dev_flag("all_autoreload", dev_mode_value)

        probe_file = resolve_probe_python_file(self.project_dir)
        compose_source = (self.project_dir / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        odoo_host_port = find_free_port()
        compose_name = f"odpm-devmode-autoreload-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory(prefix="odpm-devmode-autoreload-") as tmp:
            compose_file = Path(tmp) / "docker-compose.yml"
            compose_file.write_text(
                patch_compose_for_golden_path(compose_source, odoo_host_port),
                encoding="utf-8",
            )
            compose_argv = _compose_argv(compose_file, compose_name)

            subprocess.run(
                compose_argv + ["up", "-d"],
                cwd=self.project_dir,
                check=True,
                text=True,
            )
            try:
                url = f"http://127.0.0.1:{odoo_host_port}/web/login"
                wait_for_http_ok(
                    url,
                    timeout=DEV_MODE_TIMEOUT,
                    accept_status_codes=expected_http_status_codes(dev_mode_value),
                )

                result = run_autoreload_probe(
                    compose_argv,
                    self.project_dir,
                    probe_file,
                    trigger_timeout=DEV_MODE_RELOAD_TIMEOUT,
                )
                if result.outcome == "disabled":
                    self.fail(
                        f"{result.detail} (expected inotify in venv when dev_mode includes reload)\n"
                        f"probe_file={result.probe_file}\n"
                        f"--- logs ---\n{result.logs_excerpt}"
                    )
                if result.outcome != "activated":
                    self.fail(
                        f"{result.detail}\nprobe_file={result.probe_file}\n"
                        f"--- logs ---\n{result.logs_excerpt}"
                    )
            finally:
                subprocess.run(
                    compose_argv + ["down"],
                    cwd=self.project_dir,
                    check=False,
                    text=True,
                )


if __name__ == "__main__":
    unittest.main()
