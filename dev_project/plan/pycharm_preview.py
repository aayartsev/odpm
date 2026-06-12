"""PyCharm run configuration preview for odpm plan step evaluation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ..project_env.services.pycharm_configurator import (
    PYCHARM_RUN_CONFIG_BASENAME,
    PycharmConfigurator,
)

if TYPE_CHECKING:
    from ..config import Config
    from ..project_env import CreateProjectEnvironment


def pycharm_run_config_path(project_dir: str) -> str:
    return os.path.join(project_dir, ".run", f"{PYCHARM_RUN_CONFIG_BASENAME}.run.xml")


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
    path = pycharm_run_config_path(config.project_dir)
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
