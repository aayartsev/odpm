"""Provision a self-contained minimal odpm project for compose smoke tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from dev_project import constants

from tests.plan_smoke_helpers import seed_migrated_project_layout

FIXTURE_ROOT = Path(__file__).resolve().parent / "minimal_odpm_project"


def _stub_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "requirements.txt").write_text("", encoding="utf-8")
    (path / "odoo-bin").write_text("#!/usr/bin/env python3\n", encoding="utf-8")


def provision_minimal_odpm_project(project_dir: Path) -> Path:
    """Materialize a minimal initialized project tree under *project_dir*.

    Returns the project root (same as *project_dir*).
    """
    project_dir = project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    seed_migrated_project_layout(project_dir, include_root_compose=False)

    developing = project_dir / "developing"
    platform = project_dir / "platform" / "odoo"
    _stub_repo(developing)
    _stub_repo(platform)

    shutil.copytree(
        FIXTURE_ROOT / "developing",
        developing,
        dirs_exist_ok=True,
    )

    odpm_json = json.loads((developing / "odpm.json").read_text(encoding="utf-8"))
    odpm_json["odpm_version"] = constants.ODPM_VERSION
    odpm_json["odoo_git_link"] = platform.as_uri()
    (developing / "odpm.json").write_text(
        json.dumps(odpm_json, indent=2) + "\n",
        encoding="utf-8",
    )

    user_settings = json.loads(
        (FIXTURE_ROOT / "user_settings.json").read_text(encoding="utf-8")
    )
    user_settings["developing_project"] = developing.as_uri()
    (project_dir / "user_settings.json").write_text(
        json.dumps(user_settings, indent=2) + "\n",
        encoding="utf-8",
    )

    env_template = (FIXTURE_ROOT / "env.template").read_text(encoding="utf-8")
    (project_dir / ".env").write_text(
        env_template.format(
            BACKUP_DIR=str(project_dir / "backups"),
            ODOO_PROJECTS_DIR=str(project_dir / "unused_projects"),
        ),
        encoding="utf-8",
    )

    return project_dir
