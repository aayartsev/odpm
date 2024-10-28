import os
import pathlib
import json
import subprocess
import ast
from argparse import Namespace

from typing import TypedDict
from dataclasses import dataclass

from . import constants
from . import translations
from .inside_docker_app import cli_params

from .handle_odoo_project_git_link import HandleOdooProjectLink
from .host_user_env import CreateUserEnvironment
from .project_dir_manager import ProjectDirManager

from .protocols import CreateProjectEnvironmentProtocol
from .protocols import SystemCheckerProtocol

from .inside_docker_app.logger import get_module_logger

_logger = get_module_logger(__name__)

class OdpmJson(TypedDict):
    python_version: str
    distro_version: str
    distro_name: str
    odoo_version: str
    postgres_version: str
    dependencies: list
    requirements_txt: list

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
    arch: str
    sql_queries: list

@dataclass
class SubProject:
    subproject_dir_path: str
    subproject_rel_path: str
    list_of_modules: list
    list_of_python_packages: list

class Config():

    def __init__(self, pd_manager: ProjectDirManager, arguments: Namespace, program_dir: str, user_env: CreateUserEnvironment) -> None:
        
        self.pd_manager = pd_manager
        self.program_dir = program_dir
        self.arguments = arguments
        self.config_dict = {}
        self.repo_odpm_json = ""
        self.dockerfile_path = ""
        self.config_json_loaded = False
        self.start_string = ""
        self.project_dir = self.pd_manager.project_path
        self.config_home_dir = self.pd_manager.home_config_dir
        self.no_log_prefix = False
        self.user_env = user_env
        if self.pd_manager.init and isinstance(self.pd_manager.init, str):
            self.clone_project()
        # check current config.json file
        self.config_json_content = {}
        self.check_for_config()
        # init user settings from json file
        self.get_user_settings_json()
        self.get_user_settings()
        self.init_modules = self.beautify_module_list(self.config_dict.get("init_modules"))
        self.update_modules = self.beautify_module_list(self.config_dict.get("update_modules"))
        self.db_creation_data = self.config_dict.get("db_creation_data", constants.DEFAULT_DB_CREATION_DATA)
        self.update_git_repos = self.config_dict.get("update_git_repos", constants.DEFAULT_UPDATE_GIT_REPOS)
        self.clean_git_repos = self.config_dict.get("clean_git_repos", constants.DEFAULT_CLEAN_GIT_REPOS)
        self.check_system = self.config_dict.get("check_system", constants.DEFAULT_CHECK_SYSTEM)
        self.db_manager_password = self.config_dict.get("db_manager_password", constants.DEFAULT_DB_MANAGER_PASSWORD)
        self.dev_mode = self.config_dict.get("dev_mode", constants.DEFAULT_DEV_MODE)
        self.developing_project = self.config_dict.get("developing_project", constants.DEFAULT_DEVELOPING_PROJECT)
        self.pre_commit_map_files = self.config_dict.get("pre_commit_map_files", constants.DEFAULT_PRE_COMMIT_MAP_FILES)
        self.sql_queries = self.config_dict.get("sql_queries", constants.DEFAULT_SQL_QUERIES)
        self.use_oca_dependencies = self.config_dict.get("use_oca_dependencies", constants.DEFAULT_USE_OCA_DEPENDENCIES)
        self.create_module_links = self.config_dict.get("create_module_links", constants.DEFAULT_CREATE_MODULE_LINKS)

        # prepare developing project
        if not self.developing_project:
            _logger.error(translations.get_translation(translations.YOU_DO_NOT_SET_DEVELOPING_PROJECT))
            exit(1)
        self.developing_project = self.handle_git_link(self.developing_project, is_developing=True)
        self.developing_project_dir_path = self.developing_project.project_path
        # init project settings from odpm.json
        self.get_project_odpm_json()
        self.get_odpm_settings()

        # check for deprecated words
        self.check_file_for_deprecated_words(self.project_odpm_json)
        if not os.path.exists(self.project_odpm_json):
            self.rewrite_odpm_json()
        
        self.odoo_version = self.config_dict.get("odoo_version", 0.0)
        self.python_version = self.config_dict.get("python_version", constants.DEFAULT_PYTHON_VERSION)
        self.distro_version = self.config_dict.get("distro_version", constants.DEFAULT_DISTRO_VERSION)
        self.distro_name = self.config_dict.get("distro_name", constants.DEFAULT_DISTRO_NAME)
        self.postgres_version = self.config_dict.get("postgres_version", constants.DEFAULT_POSTGRES_VERSION)
        self.distro_version_codename = constants.DISTRO_INFO.get(self.distro_name, {}).get(self.distro_version, "")
        self.dependencies = self.config_dict.get("dependencies", [])
        self.requirements_txt = self.config_dict.get("requirements_txt", [])

        current_python_debugpy = constants.DEBUGPY.get(self.python_version, constants.DEFAULT_DEBUGPY)
        debugpy_name = current_python_debugpy.split("==")[0]
        for python_package in self.requirements_txt:
            if debugpy_name in python_package:
                self.requirements_txt.remove(python_package)
        self.requirements_txt.append(current_python_debugpy)

        # prepare dockerfile template
        self.dockerfile_template_name = f"""{self.distro_name}_{self.distro_version.replace(".", "")}_dockerfile"""
        self.project_dockerfile_template_path = os.path.join(
            self.pd_manager.project_path,
            os.path.join(constants.PROJECT_SERVICE_DIRECTORY, self.dockerfile_template_name)
        )
        self.check_file_for_deprecated_words(self.project_dockerfile_template_path)
        if not os.path.exists(self.project_dockerfile_template_path):
            self.pd_manager.rebuild_dockerfile_template(docker_template_filename=self.dockerfile_template_name)
        
        # prepare vscode settings.json template

        # prepare list of mapped dirs for  third party modules from which our project depends on
        self.dependencies_dirs = []
        self.dependencies_projects = []
        # prepare list of mapped dirs for building config file for debugger usage
        self.debugger_path_mappings = []

        # set processor architecture
        self.arch = self.config_dict.get("arch", constants.ARCH)
        if self.arch == "auto":
            self.arch = constants.ARCH
        
        self.odoo_image_name = f"""odoo-{self.arch}-python-{self.python_version}-{self.distro_name}-{self.distro_version.replace(".", "")}"""
        self.docker_project_dir = str(pathlib.PurePosixPath("/home", constants.CURRENT_USER))
        self.docker_dev_project_dir = str(pathlib.PurePosixPath(self.docker_project_dir, constants.DEV_PROJECT_DIR))
        self.docker_inside_app = str(pathlib.PurePosixPath(self.docker_dev_project_dir, "inside_docker_app"))
        self.docker_odoo_dir = str(pathlib.PurePosixPath(self.docker_project_dir, "odoo"))

        # prepare of mapped dirs for odoo addons
        self.catalogs_of_modules_data = []
        self.docker_dirs_with_addons = []
        self.docker_extra_addons = str(pathlib.PurePosixPath(self.docker_project_dir, "extra-addons"))
        if self.developing_project:
            self.docker_odoo_project_dir_path = str(pathlib.PurePosixPath(self.docker_extra_addons, self.developing_project.project_data.name))
            list_of_subprojects_data = self.check_project_for_subprojects(self.developing_project.project_path)
            if list_of_subprojects_data:
                self.catalogs_of_modules_data.extend(list_of_subprojects_data)
                for subproject in list_of_subprojects_data:
                    self.docker_dirs_with_addons.append(str(pathlib.PurePosixPath(self.docker_odoo_project_dir_path, subproject.subproject_rel_path)))
            else:
                self.docker_dirs_with_addons.append(self.docker_odoo_project_dir_path)
        odoo_addons_modules_data = self.check_project_for_subprojects(os.path.join(self.user_env.odoo_src_dir, "addons"))
        self.catalogs_of_modules_data.extend(odoo_addons_modules_data)
        self.docker_dirs_with_addons.append(str(pathlib.PurePosixPath(self.docker_odoo_dir, "addons")))
        self.docker_dirs_with_addons.append(str(pathlib.PurePosixPath(self.docker_odoo_dir, "odoo", "addons")))
        

        self.path_odoo_conf = os.path.join(self.project_dir, constants.ODOO_CONF_NAME)
        self.docker_path_odoo_conf = str(pathlib.PurePosixPath(self.docker_project_dir, constants.ODOO_CONF_NAME))
        self.docker_venv_dir = str(pathlib.PurePosixPath(self.docker_project_dir, "venv"))
        
        self.docker_backups_dir = str(pathlib.PurePosixPath(self.docker_project_dir, "backups"))
        self.docker_temp_tests_dir = str(pathlib.PurePosixPath("/tmp", "odoo_tests"))
        self.venv_dir = os.path.join(self.project_dir, "venv")
        self.docker_home = os.path.join(self.project_dir, "docker_home")
        self.dependencies_dir = os.path.join(self.project_dir, "dependencies")
        self.odoo_tests_dir = os.path.join(self.project_dir, "odoo_tests")
        self.compose_file_version = constants.DOCKER_COMPOSE_DEFAULT_FILE_VERSION
        self.odoo_config_data = {}

        # list of dirs and files which symlinks must be inside of project dir
        self.list_for_symlinks = [
            self.user_env.backups,
            self.user_env.odoo_src_dir,
            self.developing_project_dir_path,
        ]
        if self.create_module_links and os.path.exists(self.repo_odpm_json):
            self.list_for_symlinks.append(self.repo_odpm_json)
    
    @property
    def project_env(self) -> CreateProjectEnvironmentProtocol:
        """Get project_env property."""
        return self._project_env

    @project_env.setter
    def project_env(self, value: CreateProjectEnvironmentProtocol) -> None:
        """Set project_env property."""
        self._project_env = value
    
    @property
    def system_checker(self) -> SystemCheckerProtocol:
        """Get system_checker property."""
        return self._system_checker

    @system_checker.setter
    def system_checker(self, value: SystemCheckerProtocol) -> None:
        """Set system_checker property."""
        self._system_checker = value
    
    def check_project_for_subprojects(self, project_path: str) -> list[SubProject]:
        subprojects_data = {}
        list_of_subprojects = []
        set_of_python_packages = set()
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file in constants.MODULE_FILES:
                    subproject_dir_path = os.path.abspath(os.path.join(root, os.pardir))
                    if not subprojects_data.get(subproject_dir_path, False):
                        subprojects_data[subproject_dir_path] = [root]
                    else:
                        subprojects_data[subproject_dir_path].append(root)
                    list_of_python_packages_for_module = self.get_names_of_python_packages_from_manifest(os.path.abspath(os.path.join(root, file)))
                    for module in list_of_python_packages_for_module:
                        set_of_python_packages.add(module)
        for subproject_dir, module_list in subprojects_data.items():
            rel_path = os.path.relpath(subproject_dir, project_path)
            subproject = SubProject(
                subproject_dir_path=subproject_dir,
                subproject_rel_path=rel_path,
                list_of_modules=module_list,
                list_of_python_packages=list(set_of_python_packages)
            )
            list_of_subprojects.append(subproject)
        return list_of_subprojects
    
    def get_names_of_python_packages_from_manifest(self, path_to_manifest: str) -> list[str]:
        manifest_data = self.get_manifest_data(path_to_manifest)
        return manifest_data.get("external_dependencies", {}).get("python", [])
    
    def get_manifest_data(self, path_to_manifest: str) -> dict:
        manifest_data = {}
        f = open(path_to_manifest, mode='rb')
        try:
            manifest_data.update(ast.literal_eval(f.read().decode('utf-8')))
        finally:
            f.close()
        return manifest_data

    def clone_project(self) -> None:
        if cli_params.BRANCH_PARAM in self.arguments and isinstance(cli_params.BRANCH_PARAM, str):
            subprocess.run(["git", "stash"], capture_output=False)
            subprocess.run(["git", "pull"], capture_output=False)
            subprocess.run(["git", "checkout", self.arguments.branch], capture_output=False)
    
    def check_file_for_deprecated_words(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            return
        with open(file_path) as f:
            lines = f.readlines()
        remove_file = False
        for line in lines:
            for word in constants.DEPRECATED_WORDS:
                if word.lower() in line.lower():
                    remove_file = True
                    break
        if remove_file:
            dir_fo_file = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            os.rename(file_path, os.path.join(dir_fo_file, f"deprecated_{filename}"))

        

    def get_project_odpm_json(self) -> None:
        self.repo_odpm_json = os.path.join(self.developing_project.project_path, constants.PROJECT_CONFIG_FILE_NAME)
        self.project_odpm_json = os.path.join(self.project_dir, constants.PROJECT_CONFIG_FILE_NAME)
        if not os.path.exists(self.repo_odpm_json) and not os.path.exists(self.project_odpm_json):
            self.rewrite_odpm_json()

    def rewrite_odpm_json(self) -> None:
        default_odpm_json_content = self.create_default_odpm_json_content()
        with open(self.project_odpm_json, "w", encoding="utf-8") as odpm_json_file:
            json.dump(default_odpm_json_content, odpm_json_file, ensure_ascii=False, indent=4)
            
    
    def get_user_settings_json(self) -> None:
        self.user_settings_json = os.path.join(self.project_dir, constants.USER_CONFIG_FILE_NAME)
        if not os.path.exists(self.user_settings_json):
            default_user_settings_json_content = self.create_default_user_setting_json_content()
            with open(self.user_settings_json, "w", encoding="utf-8") as user_settings_json_file:
                json.dump(default_user_settings_json_content, user_settings_json_file, ensure_ascii=False, indent=4)

    def create_default_odpm_json_content(self) -> OdpmJson:
        if self.config_json_content:
            return OdpmJson(
                python_version=self.config_json_content.get("python_version", constants.DEFAULT_PYTHON_VERSION),
                distro_name=self.config_json_content.get("distro_name", constants.DEFAULT_DISTRO_NAME),
                distro_version=self.config_json_content.get("distro_version", constants.DEFAULT_DISTRO_VERSION),
                postgres_version=self.config_json_content.get("postgres_version", constants.DEFAULT_POSTGRES_VERSION),
                odoo_version=self.config_json_content.get("odoo_version", 0.0),
                dependencies=self.config_json_content.get("dependencies", []),
                requirements_txt=self.config_json_content.get("requirements_txt", []),
            )
        available_versions = [int(float(version)) for version in constants.ODOO_VERSION_DEFAULT_ENV]
        available_versions_str = ", ".join([str(float(version)) for version in available_versions])
        user_odoo_version = self.config_dict.get("odoo_version", None)
        if not user_odoo_version:
            while True:
                user_odoo_version = input(translations.get_translation(translations.SET_ODOO_VERSION).format(
                        ODOO_LATEST_VERSION=constants.ODOO_LATEST_VERSION,
                        AVAILABEL_ODOO_VERSIONS_ARE = available_versions_str,
                    ))
                try:
                    if not user_odoo_version:
                        user_odoo_version = constants.ODOO_LATEST_VERSION
                    float_version_from_user = float(user_odoo_version)
                    if str(float_version_from_user) not in available_versions_str:
                        continue
                    break
                except:
                    continue

        _logger.info(translations.get_translation(translations.YOU_SELECT_ODOO_VERSION).format(
            SELECTED_ODOO_VERSION=user_odoo_version,
        ))
        default_odpm_json_content = OdpmJson(
            python_version=self.config_dict.get("python_version",constants.ODOO_VERSION_DEFAULT_ENV[user_odoo_version]["python_version"]),
            distro_version=self.config_dict.get("distro_version",constants.ODOO_VERSION_DEFAULT_ENV[user_odoo_version]["distro_version"]),
            distro_name=self.config_dict.get("distro_name",constants.ODOO_VERSION_DEFAULT_ENV[user_odoo_version]["distro_name"]),
            postgres_version=self.config_dict.get("postgres_version", constants.DEFAULT_POSTGRES_VERSION),
            odoo_version=user_odoo_version,
            dependencies=self.config_dict.get("dependencies", []),
            requirements_txt=self.config_dict.get("requirements_txt", []),
        )
        
        return default_odpm_json_content

    def get_user_settings(self) -> None:
        if os.path.exists(self.user_settings_json):
            with open(self.user_settings_json) as user_settings_file:
                user_settings_dict = json.load(user_settings_file)
                self.config_dict = user_settings_dict
    
    def get_odpm_settings(self) -> None:
        if os.path.exists(self.project_odpm_json):
            with open(self.project_odpm_json) as project_odpm_file:
                project_odpm_dict = json.load(project_odpm_file)
                self.config_dict.update(project_odpm_dict)
        elif os.path.exists(self.repo_odpm_json):
            with open(self.repo_odpm_json) as repo_odpm_json:
                repo_odpm_json = json.load(repo_odpm_json)
                self.config_dict.update(repo_odpm_json)

    def check_for_config(self) -> None:
        self.config_json_path = os.path.join(self.project_dir, constants.CONFIG_FILE_NAME)
        self.config_deprecated_json_path = os.path.join(self.project_dir, f"deprecated_{self.config_json_path}")
        if os.path.exists(self.config_json_path):
            with open(self.config_json_path) as config_file:
                self.config_json_content = json.load(config_file)
            os.rename(self.config_json_path, self.config_deprecated_json_path)
            _logger.warning(translations.get_translation(translations.CONFIG_JSON_IS_DEPRECATED).format(
                    CONFIG_FILE_NAME=constants.CONFIG_FILE_NAME,
                ))

    
    def beautify_module_list(self, modules) -> str:
        if not modules:
            return constants.DEFAULT_LIST_OF_MODULES
        if isinstance(modules, list):
            modules = ",".join(modules)
        if isinstance(modules, str):
            modules = modules.split(",")
            modules = [module.strip() for module in modules]
            modules = ",".join(modules)
        return modules
        
    
    def create_default_user_setting_json_content(self) -> UserSettingsJson:
        user_settings_content = UserSettingsJson(
            init_modules=self.config_json_content.get("init_modules", constants.DEFAULT_INIT_MODULES),
            update_modules=self.config_json_content.get("update_modules", constants.DEFAULT_UPDATE_MODULES),
            db_creation_data=DbCreationData(
                db_lang=self.config_json_content.get("db_creation_data", {}).get("db_lang", constants.DEFAULT_DB_CREATION_DATA_DB_LANG),
                db_country_code=self.config_json_content.get("db_creation_data", {}).get("db_country_code", constants.DEFAULT_DB_CREATION_DATA_DB_COUNTRY_CODE),
                create_demo=self.config_json_content.get("db_creation_data", {}).get("create_demo", constants.DEFAULT_DB_CREATION_DATA_CREATE_DEMO),
                db_default_admin_login=self.config_json_content.get("db_creation_data", {}).get("db_default_admin_login", constants.DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_LOGIN),
                db_default_admin_password=self.config_json_content.get("db_creation_data", {}).get("db_default_admin_password", constants.DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_PASSWORD),
            ),
            update_git_repos=self.config_json_content.get("update_git_repos", constants.DEFAULT_UPDATE_GIT_REPOS),
            clean_git_repos=self.config_json_content.get("clean_git_repos", constants.DEFAULT_CLEAN_GIT_REPOS),
            check_system=self.config_json_content.get("check_system", constants.DEFAULT_CHECK_SYSTEM),
            db_manager_password=self.config_json_content.get("db_manager_password", constants.DEFAULT_DB_MANAGER_PASSWORD),
            dev_mode=self.config_json_content.get("dev_mode", constants.DEFAULT_DEV_MODE),
            developing_project=self.config_json_content.get("developing_project", self.pd_manager.init or constants.DEFAULT_DEVELOPING_PROJECT),
            pre_commit_map_files=self.config_json_content.get("pre_commit_map_files", constants.DEFAULT_PRE_COMMIT_MAP_FILES),
            sql_queries=self.config_json_content.get("sql_queries", constants.DEFAULT_SQL_QUERIES),
            use_oca_dependencies=self.config_json_content.get("use_oca_dependencies", constants.DEFAULT_USE_OCA_DEPENDENCIES), 
            create_module_links = self.config_json_content.get("create_module_links", constants.DEFAULT_CREATE_MODULE_LINKS),
        )
        return user_settings_content


    
    def handle_git_link(self, gitlink: str, is_developing: bool = False) -> HandleOdooProjectLink:
        odoo_project = HandleOdooProjectLink(
            gitlink,
            self.user_env.path_to_ssh_key,
            self.user_env.odoo_projects_dir,
            is_developing=is_developing
        )
        odoo_project.build_project()
        return odoo_project

    def config_to_json(self) -> bytes:
        config = ConfigToJson(
            docker_odoo_dir=self.docker_odoo_dir,
            odoo_config_data=self.odoo_config_data,
            docker_path_odoo_conf=self.docker_path_odoo_conf,
            arguments=vars(self.arguments),
            db_creation_data=self.db_creation_data,
            db_manager_password=self.db_manager_password,
            docker_venv_dir=self.docker_venv_dir,
            docker_project_dir=self.docker_project_dir,
            requirements_txt=self.requirements_txt,
            odoo_version=self.odoo_version,
            python_version=self.python_version,
            arch=self.arch,
            sql_queries=self.sql_queries,
        )
        return json.dumps(config).encode("utf-8")
            


