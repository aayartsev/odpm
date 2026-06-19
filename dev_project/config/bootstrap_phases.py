"""Individual bootstrap phases for :class:`~dev_project.config.config.Config`."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..debugger.user_env import resolve_debugger_backend_id
from ..translations import _
from ..dev_mode import effective_dev_mode, merge_autoreload_requirements
from ..errors import ConfigError
from ..logging import get_module_logger
from ..manifest.compat import assert_manager_supports_manifest
from .transforms import beautify_module_list
from .state import project_settings_from_raw, user_settings_from_raw

if TYPE_CHECKING:
    from .config import Config

_logger = get_module_logger(__name__)


def load_user_settings(config: Config) -> None:
    ctx = config._bootstrap_ctx
    ctx.deprecated.check_for_config()
    ctx.user_settings.get_user_settings_json()
    ctx.user_settings.get_user_settings()
    config._user = user_settings_from_raw(
        config.bootstrap.raw_user_settings,
        beautify_module_list=beautify_module_list,
    )
    config.bootstrap.developing_project = config._user.developing_project
    config.bootstrap.user_loaded = True


def bind_developing_link(config: Config) -> None:
    bootstrap = config.bootstrap
    if not bootstrap.developing_project:
        message = _("You do not set where developing project is situated. You can set it with --init command. Example: '--init file:///home/user/projects/your_directory_for_project' or directly form git repo --init https://github.com/aayartsev/odoo_demo_project.git'. You also can set it in user_settings.json file in key 'developing_project'")
        _logger.error(message)
        raise ConfigError(message)
    bootstrap.developing_project = config.handle_git_link(
        bootstrap.developing_project,
        system_type="standart",
        materialize=False,
    )
    bootstrap.developing_project_dir_path = bootstrap.developing_project.project_path
    config._developing_materializer.materialize_for_odpm_json(config)


def load_project_settings(config: Config) -> None:
    ctx = config._bootstrap_ctx
    ctx.odpm_json.get_project_odpm_json()
    ctx.odpm_json.get_odpm_settings()

    ctx.deprecated.check_file_for_deprecated_words(
        config.pd_manager.project_docker_compose_template_path
    )
    if (
        config.pd_manager.sync_templates
        and not os.path.exists(config.pd_manager.project_docker_compose_template_path)
    ):
        config.pd_manager.rebuild_docker_compose_template()

    ctx.deprecated.check_file_for_deprecated_words(config.bootstrap.repo_odpm_json)
    if not os.path.exists(config.bootstrap.repo_odpm_json):
        ctx.rewrite_odpm_json()

    assert_manager_supports_manifest(config.bootstrap.raw_odpm_json)
    config._project = project_settings_from_raw(
        config.bootstrap.raw_odpm_json,
        config.arguments,
        odoo_build_date=ctx.build_date.get_effective_odoo_build_date(),
    )
    config.bootstrap.project_loaded = True


def bind_platform_link(config: Config) -> None:
    bootstrap = config.bootstrap
    bootstrap.odoo_platform_project = config.handle_git_link(
        config.odoo_git_link,
        system_type="platform",
        materialize=False,
    )
    bootstrap.odoo_src_dir = bootstrap.odoo_platform_project.get_project_path()


def normalize_project_requirements(
    config: Config, requirements_txt: list[str]
) -> list[str]:
    normalized = config.policy.normalize_requirements(
        requirements_txt,
        python_version=config.python_version,
        odoo_version=config.odoo_version,
        debugger_backend=resolve_debugger_backend_id(
            getattr(config, "user_env", None)
        ),
    )
    return merge_autoreload_requirements(
        normalized,
        effective_dev_mode(
            config.dev_mode,
            apply_dev_mode=config.policy.apply_dev_mode,
        ),
    )
