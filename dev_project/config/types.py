from dataclasses import dataclass
from typing import TypedDict


class OdpmJson(TypedDict):
    python_version: str
    distro_version: str
    distro_name: str
    odoo_version: str
    postgres_version: str
    dependencies: list
    requirements_txt: list
    odoo_build_date: str
    odoo_git_link: str
    platform_name: str
    odpm_version: str


class DbCreationData(TypedDict):
    db_lang: str
    db_country_code: str
    create_demo: bool
    db_default_admin_login: str
    db_default_admin_password: str


class UserSettingsJson(TypedDict):
    init_modules: list
    update_modules: list
    db_creation_data: DbCreationData
    update_git_repos: bool
    clean_git_repos: bool
    check_system: bool
    db_manager_password: str
    dev_mode: str
    developing_project: str
    pre_commit_map_files: list
    sql_queries: list
    use_oca_dependencies: bool
    create_module_links: bool


class ConfigToJson(TypedDict):
    docker_odoo_dir: str
    odoo_config_data: dict
    docker_path_odoo_conf: str
    arguments: dict
    db_creation_data: DbCreationData
    db_manager_password: str
    docker_venv_dir: str
    docker_project_dir: str
    requirements_txt: list
    odoo_version: str
    python_version: str
    platform_name: str
    arch: str
    sql_queries: list
    modules_to_update: list
    docker_dirs_with_addons: list
    venv_lock_hash: str
    odpm_scenario: str
    venv_mode: str
    run_mode: str


@dataclass
class SubProject:
    subproject_dir_path: str
    subproject_rel_path: str
    list_of_modules: list
    list_of_python_packages: list
