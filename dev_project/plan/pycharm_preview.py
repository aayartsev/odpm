"""PyCharm run configuration preview for odpm plan step evaluation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ..debugger.constants import (
    DEBUGGER_BACKEND_DEBUGPY_LISTEN,
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
)
from ..project_env.services.pycharm_configurator import (
    PYCHARM_DEBUG_SERVER_RUN_CONFIG_BASENAME,
    PYCHARM_RUN_CONFIG_BASENAME,
    PycharmConfigurator,
)

if TYPE_CHECKING:
    from ..config import Config
    from ..project_env import CreateProjectEnvironment


def pycharm_run_config_basename_for_backend(backend: str) -> str | None:
    if backend == DEBUGGER_BACKEND_DEBUGPY_LISTEN:
        return PYCHARM_RUN_CONFIG_BASENAME
    if backend == DEBUGGER_BACKEND_PYDEVD_CONNECT:
        return PYCHARM_DEBUG_SERVER_RUN_CONFIG_BASENAME
    return None


def pycharm_run_config_path(project_dir: str, *, backend: str | None = None) -> str:
    basename = pycharm_run_config_basename_for_backend(
        backend or DEBUGGER_BACKEND_DEBUGPY_LISTEN
    )
    if basename is None:
        basename = PYCHARM_RUN_CONFIG_BASENAME
    return os.path.join(project_dir, ".run", f"{basename}.run.xml")


def preview_pycharm_run_config_text(
    project_env: CreateProjectEnvironment,
) -> str | None:
    try:
        configurator = PycharmConfigurator(project_env)
        profile = configurator.build_debugger_profile()
        if not configurator.should_generate(profile):
            return None
        return configurator.build_run_config_xml(profile)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def pycharm_run_config_up_to_date(
    config: Config, project_env: CreateProjectEnvironment | None = None
) -> bool:
    backend = config.user_env.debugger_backend
    path = pycharm_run_config_path(config.project_dir, backend=backend)
    if not os.path.isfile(path):
        return False
    if project_env is None:
        return True
    preview = preview_pycharm_run_config_text(project_env)
    if preview is None:
        return False
    try:
        on_disk = Path(path).read_text(encoding="utf-8")
    except OSError:
        return False
    return on_disk == preview


def pycharm_run_config_description(config: Config) -> str:
    backend = getattr(config.user_env, "debugger_backend", None)
    if backend == DEBUGGER_BACKEND_PYDEVD_CONNECT:
        return "Update PyCharm Debug Server run configuration"
    return "Update PyCharm Attach to DAP run configuration"
