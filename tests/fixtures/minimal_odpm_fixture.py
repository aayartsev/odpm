"""Provision a self-contained minimal odpm project for compose smoke tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from dev_project import constants
from dev_project.extensions.reference.mailpit import (
    MAILPIT_SERVICE_NAME,
    MAILPIT_SERVICE_SPEC,
)
from dev_project.git.deps_lock import DepsLock, LockEntry, save_deps_lock

from tests.plan_smoke_helpers import seed_migrated_project_layout

FIXTURE_ROOT = Path(__file__).resolve().parent / "minimal_odpm_project"


def _stub_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "requirements.txt").write_text("", encoding="utf-8")
    (path / "odoo-bin").write_text("#!/usr/bin/env python3\n", encoding="utf-8")


def build_v2_manifest_with_mailpit(
    *,
    platform_uri: str,
    developing_uri: str,
    flat: dict[str, Any],
    include_locks_git: bool = False,
) -> dict[str, Any]:
    """Nested manifest v2 with reference Mailpit service for compose smoke."""
    payload: dict[str, Any] = {
        "manifest_schema": constants.MANIFEST_SCHEMA_V2,
        "requires_odpm": constants.ODPM_VERSION,
        "odoo_version": flat.get("odoo_version"),
        "platform": {"git": platform_uri, "build_date": "latest"},
        "python": flat["python_version"],
        "distro": {
            "name": flat["distro_name"],
            "version": flat["distro_version"],
        },
        "postgres": flat["postgres_version"],
        "dependencies": list(flat.get("dependencies") or []),
        "requirements": list(flat.get("requirements_txt") or []),
        "developing": {"git": developing_uri},
        "services": {MAILPIT_SERVICE_NAME: dict(MAILPIT_SERVICE_SPEC)},
    }
    if include_locks_git:
        payload["locks"] = {"git": {platform_uri: "0" * 40}}
    return payload


def provision_minimal_odpm_project(
    project_dir: Path,
    *,
    scenario: str = constants.DEVELOPER_SCENARIO,
    manifest_v2_mailpit: bool = False,
    locks_drift: bool = False,
    check_system: bool = False,
    odpm_ide: str = "vscode",
) -> Path:
    """Materialize a minimal initialized project tree under *project_dir*.

    When *manifest_v2_mailpit* is true, ``developing/odpm.json`` is written as
    nested manifest v2 with the reference Mailpit ``services`` entry.

    *locks_drift* requires v2 manifest and seeds mismatched ``locks.git`` /
    ``.odpm/deps.lock.json`` via ``tests.scenario_plan_matrix_helpers.seed_locks_drift``.

    Returns the project root (same as *project_dir*).
    """
    if locks_drift and not manifest_v2_mailpit:
        raise ValueError("locks_drift requires manifest_v2_mailpit=True")

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
    platform_uri = platform.as_uri()
    developing_uri = developing.as_uri()
    if manifest_v2_mailpit:
        odpm_payload = build_v2_manifest_with_mailpit(
            platform_uri=platform_uri,
            developing_uri=developing_uri,
            flat=odpm_json,
            include_locks_git=locks_drift,
        )
    else:
        odpm_payload = dict(odpm_json)
        odpm_payload["odpm_version"] = constants.MANIFEST_V1_CONTRACT_LINE
        odpm_payload["odoo_git_link"] = platform_uri
    (developing / "odpm.json").write_text(
        json.dumps(odpm_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    user_settings = json.loads(
        (FIXTURE_ROOT / "user_settings.json").read_text(encoding="utf-8")
    )
    user_settings["developing_project"] = developing.as_uri()
    user_settings["check_system"] = check_system
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

    env_path = project_dir / ".env"
    env_lines = env_path.read_text(encoding="utf-8").splitlines()
    env_lines = [
        line if not line.startswith("ODPM_SCENARIO=") else f"ODPM_SCENARIO={scenario}"
        for line in env_lines
    ]
    if not any(line.startswith("ODPM_IDE=") for line in env_lines):
        env_lines.append(f"ODPM_IDE={odpm_ide}")
    else:
        env_lines = [
            line if not line.startswith("ODPM_IDE=") else f"ODPM_IDE={odpm_ide}"
            for line in env_lines
        ]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    if locks_drift:
        from tests.scenario_plan_matrix_helpers import seed_locks_drift

        seed_locks_drift(project_dir, platform_uri=platform_uri)
    elif not manifest_v2_mailpit:
        save_deps_lock(
            str(project_dir / constants.DEPS_LOCK_REL_PATH),
            DepsLock(
                platform=LockEntry(
                    url=platform_uri,
                    commit="e" * 40,
                    kind="file",
                )
            ),
        )

    return project_dir
