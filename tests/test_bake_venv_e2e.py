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
DOCKERFILE_CI = PROJECT_ROOT / "dev_project" / "templates" / "dockerfile_ci"


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
    def test_dockerfile_ci_uses_module_invocation(self):
        content = DOCKERFILE_CI.read_text(encoding="utf-8")
        self.assertIn("python3 -m dev_project.bake_venv", content)
        self.assertIn("{CI_VENV_INSTALL_JSON}", content)
        self.assertNotIn("bake.bake_venv", content)
        self.assertNotIn("bake_venv.py --config", content)

    def test_dockerfile_ci_creates_runtime_dir_as_root(self):
        content = DOCKERFILE_CI.read_text(encoding="utf-8")
        root_idx = content.index("USER root")
        mkdir_idx = content.index("RUN mkdir -p /run/odpm")
        bake_idx = content.index("python3 -m dev_project.bake_venv")
        self.assertLess(root_idx, mkdir_idx)
        self.assertLess(mkdir_idx, bake_idx)
        self.assertIn("chown {CONTAINER_USER}:{CONTAINER_USER} /run/odpm", content)


if __name__ == "__main__":
    unittest.main()
