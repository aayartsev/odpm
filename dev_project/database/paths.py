"""Paths and gitignore for .odpm/database runtime state."""

from __future__ import annotations

import os
from pathlib import Path

from .. import constants

_DATABASE_GITIGNORE = "*\n!.gitignore\n"


def database_dir_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_DATABASE_DIR_REL_PATH)


def last_run_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_DATABASE_LAST_RUN_REL_PATH)


def ensure_database_dir_gitignore(project_dir: str) -> None:
    database_dir = database_dir_path(project_dir)
    os.makedirs(database_dir, exist_ok=True)
    gitignore_path = os.path.join(database_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        Path(gitignore_path).write_text(_DATABASE_GITIGNORE, encoding="utf-8")
        return
    existing = Path(gitignore_path).read_text(encoding="utf-8")
    if existing.strip() != _DATABASE_GITIGNORE.strip():
        Path(gitignore_path).write_text(_DATABASE_GITIGNORE, encoding="utf-8")


def last_run_missing(project_dir: str) -> bool:
    return not os.path.isfile(last_run_path(project_dir))
