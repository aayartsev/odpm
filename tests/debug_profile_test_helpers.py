"""Shared fixtures for debugger profile and VS Code mapping tests."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

from dev_project.project_env.types import MappedPath


def make_debugger_env_mock(
    *,
    project_dir: str,
    mapped_folders: list[MappedPath],
    debugger_port: int = 5678,
    dependencies_dir: str | None = None,
    symlinks_sources: list | None = None,
) -> MagicMock:
    env = MagicMock()
    config = MagicMock()
    config.project_dir = project_dir
    config.docker_layout.dependencies_dir = dependencies_dir or os.path.join(
        project_dir, "dependencies"
    )
    config.docker_layout.symlinks_sources = symlinks_sources or []
    config.docker_layout.debugger_path_mappings = []
    env.bootstrap = MagicMock(_assembled=config)
    host_ctx = MagicMock()
    host_ctx.project_dir = project_dir
    host_ctx.docker_layout = config.docker_layout
    host_ctx.project_settings = config.project_settings
    host_ctx.policy = config.policy
    host_ctx.user_env = env.user_env
    env.host_ctx = host_ctx
    env.user_env.backups = os.path.join(project_dir, "backups")
    env.user_env.debugger_port = debugger_port
    env.user_env.debugger_backend = "debugpy_listen"
    env.mapped_folders = mapped_folders
    return env
