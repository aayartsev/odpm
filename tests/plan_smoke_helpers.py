"""Helpers for odpm --plan smoke and integration-style tests."""

from __future__ import annotations

import shutil
from pathlib import Path

from dev_project import constants


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def seed_migrated_project_layout(
    project_dir: Path,
    *,
    venv_lock_hash: str = "hash",
    include_root_compose: bool = True,
) -> None:
    """Create a minimal 4.0-style project tree for plan evaluation tests."""
    odpm_dir = project_dir / constants.PROJECT_SERVICE_DIRECTORY
    odpm_dir.mkdir(parents=True, exist_ok=True)

    runtime_dir = project_dir / constants.ODPM_RUNTIME_DIR_REL_PATH
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "config.json").write_text(
        f'{{"venv_lock_hash": "{venv_lock_hash}"}}',
        encoding="utf-8",
    )

    templates_root = repo_root() / "dev_project" / "templates"
    shutil.copy(
        templates_root / "docker-compose.yml",
        odpm_dir / "docker-compose.yml",
    )
    shutil.copy(
        templates_root / constants.DOCKERIGNORE_TEMPLATE,
        odpm_dir / constants.DOCKERIGNORE_TEMPLATE,
    )
    shutil.copy(
        templates_root / "dev_odoo_docker_config_file.conf",
        odpm_dir / "dev_odoo_docker_config_file.conf",
    )

    if include_root_compose:
        (project_dir / "docker-compose.yml").write_text(
            "# generated compose placeholder\n",
            encoding="utf-8",
        )
