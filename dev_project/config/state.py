"""Typed configuration slices populated during Config bootstrap."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..host.cli.args import OdpmCliArgs
from typing import Any, Callable, Union

from .. import constants
from ..git import HandleOdooProjectLink
from .types import DbCreationData


def user_settings_from_raw(
    raw: dict,
    *,
    beautify_module_list: Callable[[Any], str],
) -> UserSettingsState:
    return UserSettingsState(
        init_modules=beautify_module_list(raw.get("init_modules")),
        update_modules=beautify_module_list(raw.get("update_modules")),
        db_creation_data=raw.get("db_creation_data", constants.DEFAULT_DB_CREATION_DATA),
        update_git_repos=raw.get("update_git_repos", constants.DEFAULT_UPDATE_GIT_REPOS),
        clean_git_repos=raw.get("clean_git_repos", constants.DEFAULT_CLEAN_GIT_REPOS),
        check_system=raw.get("check_system", constants.DEFAULT_CHECK_SYSTEM),
        db_manager_password=raw.get(
            "db_manager_password", constants.DEFAULT_DB_MANAGER_PASSWORD
        ),
        dev_mode=raw.get("dev_mode", constants.DEFAULT_DEV_MODE),
        developing_project=raw.get(
            "developing_project", constants.DEFAULT_DEVELOPING_PROJECT
        ),
        pre_commit_map_files=raw.get(
            "pre_commit_map_files", constants.DEFAULT_PRE_COMMIT_MAP_FILES
        ),
        sql_queries=raw.get("sql_queries", constants.DEFAULT_SQL_QUERIES),
        use_oca_dependencies=raw.get(
            "use_oca_dependencies", constants.DEFAULT_USE_OCA_DEPENDENCIES
        ),
        create_module_links=raw.get(
            "create_module_links", constants.DEFAULT_CREATE_MODULE_LINKS
        ),
    )


def project_settings_from_raw(
    raw: dict,
    arguments: OdpmCliArgs,
    *,
    odoo_build_date: str,
) -> ProjectSettingsState:
    odoo_version = raw.get("odoo_version", arguments.odoo_version or 0.0)
    python_version = raw.get(
        "python_version",
        arguments.python_version or constants.DEFAULT_PYTHON_VERSION,
    )
    distro_version = raw.get(
        "distro_version",
        arguments.distro_version or constants.DEFAULT_DISTRO_VERSION,
    )
    distro_name = raw.get(
        "distro_name", arguments.distro_name or constants.DEFAULT_DISTRO_NAME
    )
    postgres_version = raw.get(
        "postgres_version",
        arguments.postgres_version or constants.DEFAULT_POSTGRES_VERSION,
    )
    return ProjectSettingsState(
        odoo_version=odoo_version,
        python_version=python_version,
        distro_version=distro_version,
        distro_name=distro_name,
        postgres_version=postgres_version,
        distro_version_codename=constants.DISTRO_INFO.get(distro_name, {}).get(
            distro_version, ""
        ),
        dependencies=raw.get("dependencies", []),
        requirements_txt=raw.get(
            "requirements_txt", arguments.requirements_txt.split(",") or []
        ),
        odoo_build_date=odoo_build_date,
        odoo_git_link=raw.get("odoo_git_link", constants.ODOO_GIT_LINK),
        platform_name=raw.get("platform_name", constants.PLATFORM_NAME),
        project_odpm_version=raw.get("odpm_version", constants.DEFAULT_ODPM_VERSION),
        arch=raw.get("arch", constants.ARCH),
    )


def _slice_property(slice_attr: str, field_name: str) -> property:
    def getter(self) -> Any:
        return getattr(getattr(self, slice_attr), field_name)

    def setter(self, value: Any) -> None:
        setattr(getattr(self, slice_attr), field_name, value)

    return property(getter, setter)


def bind_slice_properties(
    cls: type,
    slice_attr: str,
    field_names: tuple[str, ...],
) -> None:
    for field_name in field_names:
        setattr(cls, field_name, _slice_property(slice_attr, field_name))


def _ensure_bootstrap_state(self: Any) -> BootstrapState:
    state = getattr(self, "_bootstrap", None)
    if state is None:
        state = BootstrapState()
        self._bootstrap = state
    return state


def _bootstrap_property(field_name: str) -> property:
    def getter(self) -> Any:
        return getattr(_ensure_bootstrap_state(self), field_name)

    def setter(self, value: Any) -> None:
        setattr(_ensure_bootstrap_state(self), field_name, value)

    return property(getter, setter)


def bind_bootstrap_properties(cls: type) -> None:
    for field_name in BOOTSTRAP_FIELDS:
        setattr(cls, field_name, _bootstrap_property(field_name))
    for public_name, field_name in BOOTSTRAP_PRIVATE_ALIASES.items():
        setattr(cls, public_name, _bootstrap_property(field_name))


@dataclass
class BootstrapState:
    """Bootstrap-only state: git links, manifest paths, and load flags."""

    developing_project: Union[str, HandleOdooProjectLink] = (
        constants.DEFAULT_DEVELOPING_PROJECT
    )
    developing_project_dir_path: str = ""
    odoo_platform_project: HandleOdooProjectLink | None = None
    odoo_src_dir: str = ""
    repo_odpm_json: str = ""
    project_odpm_json: str = ""
    raw_user_settings: dict = field(default_factory=dict)
    raw_odpm_json: dict = field(default_factory=dict)
    user_loaded: bool = False
    project_loaded: bool = False


BOOTSTRAP_FIELDS = (
    "developing_project",
    "developing_project_dir_path",
    "odoo_platform_project",
    "odoo_src_dir",
    "repo_odpm_json",
    "project_odpm_json",
)

BOOTSTRAP_PRIVATE_ALIASES = {
    "_raw_user_settings": "raw_user_settings",
    "_raw_odpm_json": "raw_odpm_json",
    "_user_loaded": "user_loaded",
    "_project_loaded": "project_loaded",
}


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


USER_SLICE_FIELDS = tuple(
    name
    for name in UserSettingsState.__dataclass_fields__
    if name != "developing_project"
)
PROJECT_SLICE_FIELDS = tuple(ProjectSettingsState.__dataclass_fields__)
DOCKER_SLICE_FIELDS = tuple(
    name
    for name in DockerLayoutState.__dataclass_fields__
    if name != "docker_compose_command"
)
