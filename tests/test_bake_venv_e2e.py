"""Subprocess-level checks for CI bake package layout (mirrors Dockerfile.ci)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dev_project.bake_venv import VenvInstallSpec, write_ci_bake_dir

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_PROJECT_DIR = PROJECT_ROOT / "dev_project"
DOCKERFILE_CI = DEV_PROJECT_DIR / "templates" / "dockerfile_ci"


def _write_ci_context(context_dir: str) -> Path:
    """Minimal /home/odoo-like tree with bake/ package under context_dir."""
    project_dir = Path(context_dir)
    odoo_dir = project_dir / "odoo"
    odoo_dir.mkdir(parents=True)
    (odoo_dir / "requirements.txt").write_text("", encoding="utf-8")

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    spec = VenvInstallSpec(
        project_dir=str(project_dir),
        venv_dir=str(project_dir / ".venv"),
        odoo_requirements_path=str(odoo_dir / "requirements.txt"),
        extra_packages=[],
        python_version=py_version,
        lock_file_path=str(project_dir / ".venv" / ".lock"),
        lock_hash="ci-bake-e2e-lock",
    )
    write_ci_bake_dir(context_dir, spec, str(DEV_PROJECT_DIR))
    return project_dir


class BakeVenvSubprocessTests(unittest.TestCase):
    def test_bake_venv_main_reads_config_from_bake_tree(self):
        """Dockerfile.ci runs the same main() via python3 -m bake.bake_venv."""
        with tempfile.TemporaryDirectory() as context_dir:
            _write_ci_context(context_dir)
            child = f"""
import sys
from unittest.mock import patch
sys.path.insert(0, {json.dumps(context_dir)})
import bake.bake_venv as bv
with patch.object(bv, "install_fresh") as install:
    bv.main(["--config", "bake/venv_install.json"])
if not install.called:
    raise SystemExit("install_fresh was not called")
"""
            subprocess.run(
                [sys.executable, "-c", child],
                cwd=context_dir,
                check=True,
                text=True,
            )

    def test_python_m_resolves_bake_bake_venv_package(self):
        """python3 -m bake.bake_venv must resolve the bake package from WORKDIR."""
        with tempfile.TemporaryDirectory() as context_dir:
            _write_ci_context(context_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bake.bake_venv",
                    "--config",
                    "bake/venv_install.json",
                ],
                cwd=context_dir,
                capture_output=True,
                text=True,
            )
            combined = result.stdout + result.stderr
            self.assertNotIn("ModuleNotFoundError", combined)
            self.assertNotIn("No module named 'bake'", combined)

    def test_bake_entrypoint_module_importable_from_context(self):
        with tempfile.TemporaryDirectory() as context_dir:
            _write_ci_context(context_dir)
            child = f"""
import sys
sys.path.insert(0, {json.dumps(context_dir)})
import bake.inside_docker_app.main
import bake.inside_docker_app.container_bootstrap
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
        self.assertIn("python3 -m bake.bake_venv", content)
        self.assertNotIn("bake_venv.py --config", content)


if __name__ == "__main__":
    unittest.main()
