"""Typed configuration slices populated during Config bootstrap."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from .. import constants
from ..git import HandleOdooProjectLink
from .types import DbCreationData


def _slice_property(slice_attr: str, field_name: str) -> property:
    def getter(self) -> Any:
        return getattr(getattr(self, slice_attr), field_name)

    def setter(self, value: Any) -> None:
        setattr(getattr(self, slice_attr), field_name, value)

    return property(getter, setter)


@dataclass
class UserSettingsState:
    init_modules: str = constants.DEFAULT_LIST_OF_MODULES
    update_modules: str = constants.DEFAULT_LIST_OF_MODULES
    db_creation_data: DbCreationData = field(default_factory=dict)
    update_git_repos: bool = constants.DEFAULT_UPDATE_GIT_REPOS
    clean_git_repos: bool = constants.DEFAULT_CLEAN_GIT_REPOS
    check_system: bool = constants.DEFAULT_CHECK_SYSTEM
    db_manager_password: str = constants.DEFAULT_DB_MANAGER_PASSWORD
    dev_mode: str | bool = constants.DEFAULT_DEV_MODE
    developing_project: Union[str, HandleOdooProjectLink] = constants.DEFAULT_DEVELOPING_PROJECT
    pre_commit_map_files: list = field(
        default_factory=lambda: list(constants.DEFAULT_PRE_COMMIT_MAP_FILES)
    )
    sql_queries: list = field(default_factory=lambda: list(constants.DEFAULT_SQL_QUERIES))
    use_oca_dependencies: bool = constants.DEFAULT_USE_OCA_DEPENDENCIES
    create_module_links: bool = constants.DEFAULT_CREATE_MODULE_LINKS


@dataclass
class ProjectSettingsState:
    odoo_version: str | float = 0.0
    python_version: str = constants.DEFAULT_PYTHON_VERSION
    distro_version: str = constants.DEFAULT_DISTRO_VERSION
    distro_name: str = constants.DEFAULT_DISTRO_NAME
    postgres_version: str = constants.DEFAULT_POSTGRES_VERSION
    distro_version_codename: str = ""
    dependencies: list = field(default_factory=list)
    requirements_txt: list = field(default_factory=list)
    odoo_build_date: str = constants.ODOO_DEFAULT_BUILD_DATE
    odoo_git_link: str = constants.ODOO_GIT_LINK
    platform_name: str = constants.PLATFORM_NAME
    project_odpm_version: str = constants.DEFAULT_ODPM_VERSION
    arch: str = constants.ARCH


@dataclass
class DockerLayoutState:
    dockerfile_template_name: str = ""
    project_dockerfile_template_path: str = ""
    project_dockerignore_template_path: str = ""
    dependencies_dirs: list = field(default_factory=list)
    dependencies_projects: list = field(default_factory=list)
    debugger_path_mappings: list = field(default_factory=list)
    symlinks_sources: list = field(default_factory=list)
    odoo_config_data: dict = field(default_factory=dict)
    odoo_image_name: str = ""
    odoo_ci_image_name: str = ""
    ci_build_context_dir: str = ""
    docker_project_dir: str = ""
    docker_dev_project_dir: str = ""
    docker_inside_app: str = ""
    docker_odoo_dir: str = ""
    docker_extra_addons: str = ""
    path_odoo_conf: str = ""
    docker_path_odoo_conf: str = ""
    docker_venv_dir: str = ""
    docker_backups_dir: str = ""
    docker_temp_tests_dir: str = ""
    venv_dir: str = ""
    dir_for_odoo_container_home: str = ""
    dependencies_dir: str = ""
    odoo_tests_dir: str = ""
    compose_file_version: str = constants.DOCKER_COMPOSE_DEFAULT_FILE_VERSION
    docker_compose_command: str = constants.DEFAULT_DOCKER_COMPOSE_COMMAND
    docker_odoo_project_dir_path: str = ""
    list_for_symlinks: list = field(default_factory=list)
    docker_dirs_with_addons: list = field(default_factory=list)
