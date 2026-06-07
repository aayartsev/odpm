"""Docker layout and policy side-effects during Config bootstrap."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from ..dev_mode import dev_mode_disabled
from ..logging import get_module_logger
from ..scenario_policy import is_debugpy_requirement
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
    if any(is_debugpy_requirement(req) for req in original_requirements_txt):
        if not config.policy.install_debugpy:
            _logger.warning(
                "debugpy is forbidden in scenario %s and will not be installed",
                config.policy.scenario,
            )
        else:
            debugpy_req = config.policy.debugpy_requirement(config.python_version)
            _logger.info(
                "debugpy requirement normalized for scenario %s: %s",
                config.policy.scenario,
                debugpy_req,
            )

    if not dev_mode_disabled(config.dev_mode) and not config.policy.apply_dev_mode:
        _logger.warning(
            "dev_mode is ignored in scenario %s",
            config.policy.scenario,
        )

    config._paths.apply_image_names()
    config._paths.apply_docker_layout()
    config._paths.apply_developing_project_docker_path()
    config._odoo_conf.populate_addons_paths()

    config.odoo_config_data = {}
    config._paths.apply_symlink_sources()
