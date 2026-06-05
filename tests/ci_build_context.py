"""Minimal CI build context for subprocess and docker integration tests."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path, PurePosixPath

from dev_project import constants
from dev_project.bake_venv import (
    VenvInstallSpec,
    get_venv_bootstrap_packages,
    write_ci_venv_install_spec,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_PROJECT_DIR = PROJECT_ROOT / "dev_project"

DEFAULT_DOCKER_PROJECT_DIR = "/home/odoo"


def write_minimal_ci_build_context(
    context_dir: str,
    *,
    docker_project_dir: str | None = None,
    lock_hash: str = "ci-build-context-lock",
) -> Path:
    """Build a /home/odoo-like tree under *context_dir* for CI bake tests."""
    project_dir = Path(context_dir)
    docker_root = PurePosixPath(
        docker_project_dir if docker_project_dir is not None else project_dir
    )

    odoo_dir = project_dir / constants.PLATFORM_NAME
    odoo_dir.mkdir(parents=True, exist_ok=True)
    (odoo_dir / "requirements.txt").write_text("", encoding="utf-8")

    shutil.copytree(
        DEV_PROJECT_DIR,
        project_dir / constants.DEV_PROJECT_DIR,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    spec = VenvInstallSpec(
        project_dir=str(docker_root),
        venv_dir=str(docker_root / constants.VENV_DIR_NAME),
        odoo_requirements_path=str(
            docker_root / constants.PLATFORM_NAME / "requirements.txt"
        ),
        extra_packages=[],
        python_version=py_version,
        bootstrap_packages=get_venv_bootstrap_packages(py_version),
        lock_file_path=str(docker_root / constants.VENV_DIR_NAME / ".lock"),
        lock_hash=lock_hash,
    )
    write_ci_venv_install_spec(context_dir, spec)
    return project_dir
