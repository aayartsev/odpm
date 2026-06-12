"""Docker layout and policy side-effects during Config bootstrap."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from ..dev_mode import dev_mode_disabled
from ..logging import get_module_logger
from ..debugger.constants import (
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
    ODPM_IDE_NONE,
    ODPM_IDE_VSCODE,
)
from ..debugger import is_debugger_requirement
from .state import DockerLayoutState, ProjectSettingsState

if TYPE_CHECKING:
    from .config import Config

_logger = get_module_logger(__name__)


def apply_policy_and_layout(config: Config) -> None:
    from .bootstrap import normalize_project_requirements

    original_requirements_txt = list(config.requirements_txt)
    normalized_requirements = normalize_project_requirements(
        config, config.requirements_txt
    )
    arch = config._raw_odpm_json.get("arch", constants.ARCH)
    if arch == "auto":
        arch = constants.ARCH

    dockerfile_template_name = (
        f"{config.distro_name}_{config.distro_version.replace('.', '')}_dockerfile"
    )
    project_dockerfile_template_path = os.path.join(
        config.pd_manager.project_path,
        os.path.join(
            constants.PROJECT_SERVICE_DIRECTORY, dockerfile_template_name
        ),
    )
    config._bootstrap_ctx.deprecated.check_file_for_deprecated_words(
        project_dockerfile_template_path
    )
    if config.pd_manager.sync_templates:
        config.pd_manager.rebuild_dockerfile_template(
            docker_template_filename=dockerfile_template_name
        )

    project_dockerignore_template_path = os.path.join(
        config.pd_manager.project_path,
        constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
    )
    if config.pd_manager.sync_templates:
        config.pd_manager.rebuild_dockerignore_template()

    config._project = ProjectSettingsState(
        odoo_version=config.odoo_version,
        python_version=config.python_version,
        distro_version=config.distro_version,
        distro_name=config.distro_name,
        postgres_version=config.postgres_version,
        distro_version_codename=config.distro_version_codename,
        dependencies=config.dependencies,
        requirements_txt=normalized_requirements,
        odoo_build_date=config.odoo_build_date,
        odoo_git_link=config.odoo_git_link,
        platform_name=config.platform_name,
        project_odpm_version=config.project_odpm_version,
        arch=arch,
    )
    config._docker = DockerLayoutState(
        dockerfile_template_name=dockerfile_template_name,
        project_dockerfile_template_path=project_dockerfile_template_path,
        project_dockerignore_template_path=project_dockerignore_template_path,
    )
    if any(is_debugger_requirement(req) for req in original_requirements_txt):
        if not config.policy.install_debugpy:
            _logger.warning(
                "debugger packages are forbidden in scenario %s and will not be installed",
                config.policy.scenario,
            )
        else:
            normalized_debugger = [
                req
                for req in normalized_requirements
                if is_debugger_requirement(req)
            ]
            if normalized_debugger:
                _logger.info(
                    "debugger requirement normalized for scenario %s: %s",
                    config.policy.scenario,
                    normalized_debugger[0],
                )

    if not dev_mode_disabled(config.dev_mode) and not config.policy.apply_dev_mode:
        _logger.warning(
            "dev_mode is ignored in scenario %s",
            config.policy.scenario,
        )

    if (
        config.user_env.debugger_backend == DEBUGGER_BACKEND_PYDEVD_CONNECT
        and config.user_env.odpm_ide == ODPM_IDE_VSCODE
    ):
        _logger.warning(
            "ODPM_DEBUGGER_BACKEND=pydevd_connect is incompatible with ODPM_IDE=vscode; "
            "use ODPM_IDE=pycharm or both"
        )

    if (
        config.user_env.debugger_backend == DEBUGGER_BACKEND_PYDEVD_CONNECT
        and config.user_env.odpm_ide == ODPM_IDE_NONE
    ):
        _logger.warning(
            "ODPM_DEBUGGER_BACKEND=pydevd_connect with ODPM_IDE=none; "
            "set ODPM_IDE=pycharm or both to generate Debug Server XML"
        )

    ctx = config._bootstrap_ctx
    ctx.paths.apply_image_names()
    ctx.paths.apply_docker_layout()
    ctx.paths.apply_developing_project_docker_path()
    ctx.odoo_conf.populate_addons_paths()

    config.odoo_config_data = {}
    ctx.paths.apply_symlink_sources()
