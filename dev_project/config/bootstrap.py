"""Ordered bootstrap phases for :class:`~dev_project.config.config.Config`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..host.cli.args import OdpmCliArgs

from ..git.developing_repo_materializer import DevelopingRepoMaterializer
from ..host.runtime import HostRuntimeState
from ..host.user_env import CreateUserEnvironment
from ..project_dir_manager import ProjectDirManager
from ..scenario_policy import ScenarioPolicy
from .bootstrap_context import ConfigBootstrapContext
from .bootstrap_phases import (
    bind_developing_link,
    bind_platform_link,
    load_project_settings,
    load_user_settings,
    normalize_project_requirements,
)
from .layout import apply_policy_and_layout
from .state import (
    BootstrapState,
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
)

if TYPE_CHECKING:
    from .config import Config

__all__ = [
    "bind_developing_link",
    "bind_platform_link",
    "bootstrap_config",
    "init_context",
    "load_project_settings",
    "load_user_settings",
    "normalize_project_requirements",
]


def bootstrap_config(
    config: Config,
    pd_manager: ProjectDirManager,
    arguments: OdpmCliArgs,
    program_dir: str,
    user_env: CreateUserEnvironment,
) -> None:
    """Run all host configuration bootstrap phases in order."""
    init_context(config, pd_manager, arguments, program_dir, user_env)
    load_user_settings(config)
    bind_developing_link(config)
    load_project_settings(config)
    bind_platform_link(config)
    apply_policy_and_layout(config)


def init_context(
    config: Config,
    pd_manager: ProjectDirManager,
    arguments: OdpmCliArgs,
    program_dir: str,
    user_env: CreateUserEnvironment,
) -> None:
    config.pd_manager = pd_manager
    config.program_dir = program_dir
    config.arguments = arguments
    config._bootstrap = BootstrapState()
    config.dockerfile_path = ""
    config.config_json_loaded = False
    config._runtime = HostRuntimeState()
    config.project_dir = config.pd_manager.project_path
    config.config_home_dir = config.pd_manager.home_config_dir
    config.user_env = user_env
    config.policy = ScenarioPolicy.from_scenario(config.user_env.odpm_scenario)
    config._user = UserSettingsState()
    config._project = ProjectSettingsState()
    config._docker = DockerLayoutState()
    config._bootstrap_ctx = ConfigBootstrapContext(
        config,
        bind_platform_link=bind_platform_link,
    )
    config._paths = config._bootstrap_ctx.paths
    config._odoo_conf = config._bootstrap_ctx.odoo_conf
    config._git_repos = config._bootstrap_ctx.git_repos
    config.postgres_data_local_storage = (
        config._bootstrap_ctx.paths.get_postgres_data_local_storage_path()
    )
    config.config_json_content = {}
    config._developing_materializer = DevelopingRepoMaterializer()
