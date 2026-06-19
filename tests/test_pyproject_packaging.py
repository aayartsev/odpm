"""Contract tests for pip/PyPI packaging metadata."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_SUBPROCESS_TEXT = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"}


def _prepare_minimal_build_tree(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("pyproject.toml", "README.MD", "odpm.py"):
        shutil.copy2(PROJECT_ROOT / name, dest / name)
    shutil.copytree(PROJECT_ROOT / "dev_project", dest / "dev_project")


def _load_pyproject() -> dict:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


class PyprojectPackagingTests(unittest.TestCase):
    def test_project_identity_and_entrypoint(self):
        project = _load_pyproject()["project"]
        self.assertEqual(project["name"], "odpm")
        self.assertEqual(project["requires-python"], ">=3.10")
        self.assertEqual(project["scripts"]["odpm"], "dev_project.cli:main")

    def test_runtime_dependencies_include_packaging(self):
        dependencies = _load_pyproject()["project"]["dependencies"]
        self.assertTrue(any(dep.startswith("packaging>=") for dep in dependencies))

    def test_project_urls_and_license(self):
        project = _load_pyproject()["project"]
        self.assertEqual(project["license"], {"file": "LICENSE"})
        urls = project["urls"]
        self.assertIn("Repository", urls)
        self.assertIn("github.com/aayartsev/odpm", urls["Repository"])

    def test_dynamic_version_from_constants(self):
        dynamic = _load_pyproject()["project"]["dynamic"]
        self.assertIn("version", dynamic)
        version_attr = _load_pyproject()["tool"]["setuptools"]["dynamic"]["version"]["attr"]
        self.assertEqual(version_attr, "dev_project.constants.ODPM_VERSION")

    def test_wheel_build_produces_single_wheel(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp) / "src"
            _prepare_minimal_build_tree(workdir)
            venv_dir = Path(tmp) / "venv"
            dist_dir = Path(tmp) / "dist"
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True,
                **_SUBPROCESS_TEXT,
            )
            venv_python = venv_dir / "bin" / "python"
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "build"],
                check=True,
                **_SUBPROCESS_TEXT,
            )
            completed = subprocess.run(
                [
                    str(venv_python),
                    "-m",
                    "build",
                    "--outdir",
                    str(dist_dir),
                ],
                cwd=workdir,
                **_SUBPROCESS_TEXT,
            )
            self.assertEqual(
                completed.returncode,
                0,
                msg=completed.stderr or completed.stdout,
            )
            wheels = list(dist_dir.glob("odpm-*.whl"))
            self.assertEqual(len(wheels), 1)
            self.assertTrue(wheels[0].name.endswith(".whl"))


if __name__ == "__main__":
    unittest.main()
