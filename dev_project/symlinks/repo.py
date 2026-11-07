"""Incremental project symlinks after each git repo is processed."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal

from .manager import SymlinkManager

if TYPE_CHECKING:
    from ..host.context import HostProjectContext
    from ..host.ports import BootstrapHandle

SymlinkScope = Literal["project", "dependency"]


def _symlink_host_view(
    bootstrap: BootstrapHandle,
    host_ctx: HostProjectContext | None = None,
):
    """Narrow host view for symlink helpers at the AssembledProject/bootstrap boundary.

    Avoids full ``HostProjectContext.from_config`` so incomplete AssembledProject stubs
    used in bootstrap unit tests still get project links.
    """
    if host_ctx is not None:
        return host_ctx
    config = bootstrap
    addon = getattr(config, "addon_layout", None)
    if addon is None:
        addon = SimpleNamespace(catalogs_of_modules_data=[])
    return SimpleNamespace(
        project_dir=getattr(config, "project_dir", "") or "",
        docker_layout=config.docker_layout,
        project_settings=getattr(config, "project_settings", None),
        user_settings=getattr(config, "user_settings", None),
        addon_layout=addon,
    )


def ensure_git_repo_symlink(
    bootstrap: BootstrapHandle,
    target_path: str,
    *,
    scope: SymlinkScope = "project",
    host_ctx: HostProjectContext | None = None,
) -> None:
    if not target_path:
        return
    ctx = _symlink_host_view(bootstrap, host_ctx)
    if not ctx.project_dir:
        return
    manager = SymlinkManager(bootstrap, host_ctx=ctx)
    if scope == "dependency":
        manager.ensure_dependency_repo_link(target_path)
        if target_path not in ctx.docker_layout.dependencies_dirs:
            ctx.docker_layout.dependencies_dirs.append(target_path)
        return
    manager.ensure_project_repo_link(target_path)


def ensure_developing_repo_symlinks(
    bootstrap: BootstrapHandle,
    *,
    host_ctx: HostProjectContext | None = None,
) -> None:
    developing = bootstrap.developing_project
    if not developing or not developing.project_path:
        return
    ensure_git_repo_symlink(
        bootstrap, developing.project_path, scope="project", host_ctx=host_ctx
    )
    repo_odpm_json = bootstrap.repo_odpm_json
    if not isinstance(repo_odpm_json, str):
        flat = bootstrap.repo_odpm_json
        repo_odpm_json = flat if isinstance(flat, str) else ""
    if repo_odpm_json and os.path.exists(repo_odpm_json):
        ensure_git_repo_symlink(
            bootstrap, repo_odpm_json, scope="project", host_ctx=host_ctx
        )
