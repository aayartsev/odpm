"""Ordered bootstrap phases for :class:`~dev_project.config.config.Config`."""

from __future__ import annotations

import os
from argparse import Namespace
from typing import TYPE_CHECKING

from .. import constants, translations
from ..dev_mode import effective_dev_mode, merge_autoreload_requirements
from ..errors import ConfigError
from ..git.developing_repo_materializer import DevelopingRepoMaterializer
from ..host_runtime import HostRuntimeState
from ..host_user_env import CreateUserEnvironment
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..scenario_policy import ScenarioPolicy
from .git_repos import GitRepoCoordinator
from .layout import apply_policy_and_layout
from .loader import ConfigLoader
from .odoo_conf import OdooConfBuilder
from .paths import ConfigPaths
from .state import (
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
    project_settings_from_raw,
    user_settings_from_raw,
)

if TYPE_CHECKING:
    from .config import Config

_logger = get_module_logger(__name__)


def bootstrap_config(
    config: Config,
    pd_manager: ProjectDirManager,
    arguments: Namespace,
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
    arguments: Namespace,
    program_dir: str,
    user_env: CreateUserEnvironment,
) -> None:
    config.pd_manager = pd_manager
    config.program_dir = program_dir
    config.arguments = arguments
    config._raw_user_settings = {}
    config._raw_odpm_json = {}
    config._user_loaded = False
    config._project_loaded = False
    config.repo_odpm_json = ""
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
    config._loader = ConfigLoader(config)
    config._paths = ConfigPaths(config)
    config._odoo_conf = OdooConfBuilder(config)
    config._git_repos = GitRepoCoordinator(config)
    config.postgres_data_local_storage = (
        config._paths.get_postgres_data_local_storage_path()
    )
    config.config_json_content = {}
    config._developing_materializer = DevelopingRepoMaterializer()


def load_user_settings(config: Config) -> None:
    config._loader.check_for_config()
    config._loader.get_user_settings_json()
    config._loader.get_user_settings()
    config._user = user_settings_from_raw(
        config._raw_user_settings,
        beautify_module_list=config._loader.beautify_module_list,
    )
    config._user_loaded = True


def bind_developing_link(config: Config) -> None:
    if not config.developing_project:
        message = translations.get_translation(
            translations.YOU_DO_NOT_SET_DEVELOPING_PROJECT
        )
        _logger.error(message)
        raise ConfigError(message)
    config.developing_project = config.handle_git_link(
        config.developing_project,
        system_type="standart",
        materialize=False,
    )
    config.developing_project_dir_path = config.developing_project.project_path
    config._developing_materializer.materialize_for_odpm_json(config)


def load_project_settings(config: Config) -> None:
    config._loader.get_project_odpm_json()
    config._loader.get_odpm_settings()

    config._loader.check_file_for_deprecated_words(
        config.pd_manager.project_docker_compose_template_path
    )
    if (
        config.pd_manager.sync_templates
        and not os.path.exists(config.pd_manager.project_docker_compose_template_path)
    ):
        config.pd_manager.rebuild_docker_compose_template()

    config._loader.check_file_for_deprecated_words(config.repo_odpm_json)
    if not os.path.exists(config.repo_odpm_json):
        config._loader.rewrite_odpm_json()

    config._project = project_settings_from_raw(
        config._raw_odpm_json,
        config.arguments,
        odoo_build_date=config._loader.get_effective_odoo_build_date(),
    )
    if float(config.project_odpm_version) < float(constants.ODPM_VERSION):
        message = translations.get_translation(
            translations.PROJECT_ODPM_VERSION_LESS_CURRENT_ODPM_VERSION
        ).format(
            PROJECT_ODPM_VERSION=config.project_odpm_version,
            ODPM_VERSION=constants.ODPM_VERSION,
        )
        _logger.warning(message)
        raise ConfigError(message)
    config._project_loaded = True


def bind_platform_link(config: Config) -> None:
    config.odoo_platform_project = config.handle_git_link(
        config.odoo_git_link,
        system_type="platform",
        materialize=False,
    )
    config.odoo_src_dir = config.odoo_platform_project.get_project_path()


def normalize_project_requirements(
    config: Config, requirements_txt: list[str]
) -> list[str]:
    normalized = config.policy.normalize_requirements(
        requirements_txt,
        python_version=config.python_version,
    )
    return merge_autoreload_requirements(
        normalized,
        effective_dev_mode(
            config.dev_mode,
            apply_dev_mode=config.policy.apply_dev_mode,
        ),
    )
