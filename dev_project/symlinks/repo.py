"""Incremental project symlinks after each git repo is processed."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

from .manager import SymlinkManager

if TYPE_CHECKING:
    from ..config.config import Config

SymlinkScope = Literal["project", "dependency"]


def ensure_git_repo_symlink(
    config: Config,
    target_path: str,
    *,
    scope: SymlinkScope = "project",
) -> None:
    if not target_path or not getattr(config, "project_dir", None):
        return
    manager = SymlinkManager(config)
    if scope == "dependency":
        manager.ensure_dependency_repo_link(target_path)
        if target_path not in config.dependencies_dirs:
            config.dependencies_dirs.append(target_path)
        return
    manager.ensure_project_repo_link(target_path)


def ensure_developing_repo_symlinks(config: Config) -> None:
    developing = getattr(config, "developing_project", None)
    if not developing or not developing.project_path:
        return
    ensure_git_repo_symlink(config, developing.project_path, scope="project")
    repo_odpm_json = getattr(config, "repo_odpm_json", "") or ""
    if (
        isinstance(repo_odpm_json, str)
        and repo_odpm_json
        and os.path.exists(repo_odpm_json)
    ):
        ensure_git_repo_symlink(config, repo_odpm_json, scope="project")
