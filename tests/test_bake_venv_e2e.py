"""Subprocess-level checks for CI build context (mirrors Dockerfile.ci)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from tests.ci_build_context import write_minimal_ci_build_context

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE_PLATFORM = (
    PROJECT_ROOT / "dev_project" / "templates" / "dockerfile_platform"
)


def _write_ci_context(context_dir: str) -> Path:
    return write_minimal_ci_build_context(
        context_dir,
        lock_hash="ci-bake-e2e-lock",
    )


class BakeVenvSubprocessTests(unittest.TestCase):
    def test_bake_venv_main_reads_config_from_ci_tree(self):
        """Dockerfile.ci runs the same main() via python3 -m dev_project.bake_venv."""
        with tempfile.TemporaryDirectory() as context_dir:
            _write_ci_context(context_dir)
            child = f"""
import sys
from unittest.mock import patch
sys.path.insert(0, {json.dumps(context_dir)})
import dev_project.bake_venv as bv
with patch.object(bv, "install_fresh") as install:
    bv.main(["--config", {json.dumps(constants.CI_VENV_INSTALL_JSON)}])
if not install.called:
    raise SystemExit("install_fresh was not called")
"""
            subprocess.run(
                [sys.executable, "-c", child],
                cwd=context_dir,
                check=True,
                text=True,
            )

    def test_python_m_resolves_dev_project_bake_venv_package(self):
        """python3 -m dev_project.bake_venv must resolve from WORKDIR."""
        with tempfile.TemporaryDirectory() as context_dir:
            _write_ci_context(context_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "dev_project.bake_venv",
                    "--config",
                    constants.CI_VENV_INSTALL_JSON,
                ],
                cwd=context_dir,
                capture_output=True,
                text=True,
            )
            combined = result.stdout + result.stderr
            self.assertNotIn("ModuleNotFoundError", combined)
            self.assertNotIn("No module named 'dev_project'", combined)

    def test_dev_entrypoint_module_importable_from_context(self):
        with tempfile.TemporaryDirectory() as context_dir:
            _write_ci_context(context_dir)
            child = f"""
import sys
sys.path.insert(0, {json.dumps(context_dir)})
import dev_project.inside_docker_app.run_odoo
import dev_project.inside_docker_app.container_bootstrap
"""
            subprocess.run(
                [sys.executable, "-c", child],
                cwd=context_dir,
                check=True,
                text=True,
            )


class CiDockerfileTests(unittest.TestCase):
    def test_dockerfile_platform_has_no_bake_venv(self):
        content = DOCKERFILE_PLATFORM.read_text(encoding="utf-8")
        self.assertNotIn("bake_venv", content)

    def test_dockerfile_venv_uses_module_invocation(self):
        content = (
            PROJECT_ROOT / "dev_project" / "templates" / "dockerfile_venv"
        ).read_text(encoding="utf-8")
        self.assertIn("python3 -m dev_project.bake_venv", content)
        self.assertIn("ci/venv_install.json", content)
        self.assertNotIn("bake.bake_venv", content)
        self.assertNotIn("bake_venv.py --config", content)

    def test_dockerfile_app_has_no_bake_venv(self):
        app = (
            PROJECT_ROOT / "dev_project" / "templates" / "dockerfile_app"
        ).read_text(encoding="utf-8")
        self.assertNotIn("bake_venv", app)
        self.assertIn("runtime/config.json", app)

    def test_dockerfile_app_has_no_run_mkdir_odpm(self):
        app = (
            PROJECT_ROOT / "dev_project" / "templates" / "dockerfile_app"
        ).read_text(encoding="utf-8")
        self.assertNotIn("RUN mkdir", app)
        self.assertIn("/run/odpm/config.json", app)
        self.assertNotIn("USER root", app)


if __name__ == "__main__":
    unittest.main()
