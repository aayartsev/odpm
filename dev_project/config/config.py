import os
from argparse import Namespace
from typing import Literal

from .. import constants, translations
from ..errors import ConfigError
from ..git import HandleOdooProjectLink
from ..host_user_env import CreateUserEnvironment
from ..inside_docker_app.logger import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..protocols import CreateProjectEnvironmentProtocol, SystemCheckerProtocol
from ..scenario_policy import ScenarioPolicy, is_debugpy_requirement
from .loader import ConfigLoader
from .odoo_conf import OdooConfBuilder
from .paths import ConfigPaths
from .payload import compute_venv_lock_hash, config_to_json
from .types import SubProject

_logger = get_module_logger(__name__)


class Config:
    policy: ScenarioPolicy

    def __init__(
        self,
        pd_manager: ProjectDirManager,
        arguments: Namespace,
        program_dir: str,
        user_env: CreateUserEnvironment,
    ) -> None:
        self._init_context(pd_manager, arguments, program_dir, user_env)
        self._load_user_settings()
        self._bind_developing_link()
        self._load_project_settings()
        self._bind_platform_link()
        self._apply_policy_and_layout()

    def _init_context(
        self,
        pd_manager: ProjectDirManager,
        arguments: Namespace,
        program_dir: str,
        user_env: CreateUserEnvironment,
    ) -> None:
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
        self.policy = ScenarioPolicy.from_scenario(self.user_env.odpm_scenario)
        self.platform_name = constants.PLATFORM_NAME
        self._loader = ConfigLoader(self)
        self._paths = ConfigPaths(self)
        self._odoo_conf = OdooConfBuilder(self)
        self.postgres_data_local_storage = (
            self._paths.get_postgres_data_local_storage_path()
        )
        self.config_json_content = {}
        self._developing_repo_materialized = False

    def _load_user_settings(self) -> None:
        self._loader.check_for_config()
        self._loader.get_user_settings_json()
        self._loader.get_user_settings()
        self.init_modules = self._loader.beautify_module_list(
            self.config_dict.get("init_modules")
        )
        self.update_modules = self._loader.beautify_module_list(
            self.config_dict.get("update_modules")
        )
        self.db_creation_data = self.config_dict.get(
            "db_creation_data", constants.DEFAULT_DB_CREATION_DATA
        )
        self.update_git_repos = self.config_dict.get(
            "update_git_repos", constants.DEFAULT_UPDATE_GIT_REPOS
        )
        self.clean_git_repos = self.config_dict.get(
            "clean_git_repos", constants.DEFAULT_CLEAN_GIT_REPOS
        )
        self.check_system = self.config_dict.get(
            "check_system", constants.DEFAULT_CHECK_SYSTEM
        )
        self.db_manager_password = self.config_dict.get(
            "db_manager_password", constants.DEFAULT_DB_MANAGER_PASSWORD
        )
        self.dev_mode = self.config_dict.get("dev_mode", constants.DEFAULT_DEV_MODE)
        self.developing_project = self.config_dict.get(
            "developing_project", constants.DEFAULT_DEVELOPING_PROJECT
        )
        self.pre_commit_map_files = self.config_dict.get(
            "pre_commit_map_files", constants.DEFAULT_PRE_COMMIT_MAP_FILES
        )
        self.sql_queries = self.config_dict.get(
            "sql_queries", constants.DEFAULT_SQL_QUERIES
        )
        self.use_oca_dependencies = self.config_dict.get(
            "use_oca_dependencies", constants.DEFAULT_USE_OCA_DEPENDENCIES
        )
        self.create_module_links = self.config_dict.get(
            "create_module_links", constants.DEFAULT_CREATE_MODULE_LINKS
        )

    def _bind_developing_link(self) -> None:
        if not self.developing_project:
            message = translations.get_translation(
                translations.YOU_DO_NOT_SET_DEVELOPING_PROJECT
            )
            _logger.error(message)
            raise ConfigError(message)
        self.developing_project = self.handle_git_link(
            self.developing_project,
            system_type="standart",
            materialize=False,
        )
        self.developing_project_dir_path = self.developing_project.project_path
        self._ensure_developing_project_for_odpm_json()

    def _is_remote_git_link(self, link: HandleOdooProjectLink) -> bool:
        return link.link_type in (
            constants.GITLINK_TYPE_HTTP,
            constants.GITLINK_TYPE_GIT,
            constants.GITLINK_TYPE_SSH,
        )

    def _ensure_developing_project_for_odpm_json(self) -> None:
        """Clone developing repo before reading odpm.json when it lives in git."""
        if not self._is_remote_git_link(self.developing_project):
            return
        if self.skip_git_update():
            return
        repo_odpm_json = os.path.join(
            self.developing_project.project_path,
            constants.PROJECT_CONFIG_FILE_NAME,
        )
        project_odpm_json = os.path.join(
            self.project_dir, constants.PROJECT_CONFIG_FILE_NAME
        )
        if os.path.exists(repo_odpm_json) or os.path.exists(project_odpm_json):
            return
        self.developing_project.build_project()
        if self.arguments.branch and isinstance(self.arguments.branch, str):
            self.developing_project.switch_to_branch(self.arguments.branch)
        self.developing_project_dir_path = self.developing_project.project_path
        self._developing_repo_materialized = True

    def _load_project_settings(self) -> None:
        self._loader.get_project_odpm_json()
        self._loader.get_odpm_settings()

        self._loader.check_file_for_deprecated_words(
            self.pd_manager.project_docker_compose_template_path
        )
        if not os.path.exists(self.pd_manager.project_docker_compose_template_path):
            self.pd_manager.rebuild_docker_compose_template()

        self._loader.check_file_for_deprecated_words(self.repo_odpm_json)
        if not os.path.exists(self.repo_odpm_json):
            self._loader.rewrite_odpm_json()

        self.odoo_version = self.config_dict.get(
            "odoo_version", self.arguments.odoo_version or 0.0
        )
        self.python_version = self.config_dict.get(
            "python_version",
            self.arguments.python_version or constants.DEFAULT_PYTHON_VERSION,
        )
        self.distro_version = self.config_dict.get(
            "distro_version",
            self.arguments.distro_version or constants.DEFAULT_DISTRO_VERSION,
        )
        self.distro_name = self.config_dict.get(
            "distro_name", self.arguments.distro_name or constants.DEFAULT_DISTRO_NAME
        )
        self.postgres_version = self.config_dict.get(
            "postgres_version",
            self.arguments.postgres_version or constants.DEFAULT_POSTGRES_VERSION,
        )
        self.distro_version_codename = constants.DISTRO_INFO.get(
            self.distro_name, {}
        ).get(self.distro_version, "")
        self.dependencies = self.config_dict.get("dependencies", [])
        self.requirements_txt = self.config_dict.get(
            "requirements_txt", self.arguments.requirements_txt.split(",") or []
        )
        self.odoo_build_date = self._loader.get_effective_odoo_build_date()
        self.odoo_git_link = self.config_dict.get(
            "odoo_git_link", constants.ODOO_GIT_LINK
        )
        self.platform_name = self.config_dict.get(
            "platform_name", constants.PLATFORM_NAME
        )
        self.project_odpm_version = self.config_dict.get(
            "odpm_version", constants.DEFAULT_ODPM_VERSION
        )
        if float(self.project_odpm_version) < float(constants.ODPM_VERSION):
            message = translations.get_translation(
                translations.PROJECT_ODPM_VERSION_LESS_CURRENT_ODPM_VERSION
            ).format(
                PROJECT_ODPM_VERSION=self.project_odpm_version,
                ODPM_VERSION=constants.ODPM_VERSION,
            )
            _logger.warning(message)
            raise ConfigError(message)

    def _bind_platform_link(self) -> None:
        self.odoo_platform_project = self.handle_git_link(
            self.odoo_git_link,
            system_type="platform",
            materialize=False,
        )
        self.odoo_src_dir = self.odoo_platform_project.get_project_path()

    def _apply_policy_and_layout(self) -> None:
        original_requirements_txt = list(self.requirements_txt)
        self.requirements_txt = self.policy.normalize_requirements(
            self.requirements_txt,
            python_version=self.python_version,
        )
        if any(is_debugpy_requirement(req) for req in original_requirements_txt):
            if not self.policy.install_debugpy:
                _logger.warning(
                    "debugpy is forbidden in scenario %s and will not be installed",
                    self.policy.scenario,
                )
            else:
                debugpy_req = self.policy.debugpy_requirement(self.python_version)
                _logger.info(
                    "debugpy requirement normalized for scenario %s: %s",
                    self.policy.scenario,
                    debugpy_req,
                )

        self.dockerfile_template_name = (
            f"{self.distro_name}_{self.distro_version.replace('.', '')}_dockerfile"
        )
        self.project_dockerfile_template_path = os.path.join(
            self.pd_manager.project_path,
            os.path.join(
                constants.PROJECT_SERVICE_DIRECTORY, self.dockerfile_template_name
            ),
        )
        self._loader.check_file_for_deprecated_words(self.project_dockerfile_template_path)
        self.pd_manager.rebuild_dockerfile_template(
            docker_template_filename=self.dockerfile_template_name
        )

        self.project_dockerignore_template_path = os.path.join(
            self.pd_manager.project_path,
            constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        self.pd_manager.rebuild_dockerignore_template()

        self.dependencies_dirs = []
        self.dependencies_projects = []
        self.debugger_path_mappings = []
        self.symlinks_sources = []
        self.arch = self.config_dict.get("arch", constants.ARCH)
        if self.arch == "auto":
            self.arch = constants.ARCH

        self._paths.apply_image_names()
        self._paths.apply_docker_layout()
        self._paths.apply_developing_project_docker_path()
        self._odoo_conf.populate_addons_paths()

        self.odoo_config_data = {}
        self._paths.apply_symlink_sources()

    def skip_git_update(self) -> bool:
        return bool(getattr(self.arguments, "no_git_update", False))

    def ensure_git_repos_present(self) -> None:
        missing: list[str] = []
        for label, path in (
            ("platform", self.odoo_src_dir),
            ("developing", self.developing_project_dir_path),
        ):
            if not path or not os.path.isdir(path):
                missing.append(f"{label}: {path or '<unset>'}")
        if missing:
            message = (
                "--no-git-update requires existing local repository directories: "
                + ", ".join(missing)
            )
            _logger.error(message)
            raise ConfigError(message)

    def materialize_git_repos(self) -> None:
        if not self._developing_repo_materialized:
            self.developing_project.build_project()
            if self.arguments.branch and isinstance(self.arguments.branch, str):
                self.developing_project.switch_to_branch(self.arguments.branch)
            self.developing_project_dir_path = self.developing_project.project_path

        self.odoo_platform_project.build_project()
        self.apply_odoo_build_date_to_platform()

        self._paths.apply_developing_project_docker_path()

    @property
    def project_env(self) -> CreateProjectEnvironmentProtocol:
        return self._project_env

    @project_env.setter
    def project_env(self, value: CreateProjectEnvironmentProtocol) -> None:
        self._project_env = value

    @property
    def system_checker(self) -> SystemCheckerProtocol:
        return self._system_checker

    @system_checker.setter
    def system_checker(self, value: SystemCheckerProtocol) -> None:
        self._system_checker = value

    def get_postgres_data_local_storage_path(self) -> str:
        return self._paths.get_postgres_data_local_storage_path()

    def check_project_for_subprojects(self, project_path: str) -> list[SubProject]:
        return self._odoo_conf.check_project_for_subprojects(project_path)

    def get_names_of_python_packages_from_manifest(
        self, path_to_manifest: str
    ) -> list[str]:
        return self._odoo_conf.get_names_of_python_packages_from_manifest(
            path_to_manifest
        )

    def get_manifest_data(self, path_to_manifest: str) -> dict:
        return self._odoo_conf.get_manifest_data(path_to_manifest)

    def check_file_for_deprecated_words(self, file_path: str) -> None:
        self._loader.check_file_for_deprecated_words(file_path)

    def get_project_odpm_json(self) -> None:
        self._loader.get_project_odpm_json()

    def rewrite_odpm_json(self) -> None:
        self._loader.rewrite_odpm_json()

    def get_user_settings_json(self) -> None:
        self._loader.get_user_settings_json()

    def create_default_odpm_json_content(self):
        return self._loader.create_default_odpm_json_content()

    def get_user_settings(self) -> None:
        self._loader.get_user_settings()

    def get_odpm_settings(self) -> None:
        self._loader.get_odpm_settings()

    def check_for_config(self) -> None:
        self._loader.check_for_config()

    def beautify_module_list(self, modules) -> str:
        return self._loader.beautify_module_list(modules)

    def create_default_user_setting_json_content(self):
        return self._loader.create_default_user_setting_json_content()

    def get_developing_project_link(self) -> str:
        return self._loader.get_developing_project_link()

    def handle_git_link(
        self,
        gitlink: str,
        system_type: Literal["developing", "platform", "standart"] = "standart",
        *,
        materialize: bool = False,
    ) -> HandleOdooProjectLink:
        odoo_project = HandleOdooProjectLink(
            gitlink,
            self.user_env.path_to_ssh_key,
            self.user_env.odoo_projects_dir,
            system_type=system_type,
        )
        if materialize:
            odoo_project.build_project()
        return odoo_project

    def compute_venv_lock_hash(self) -> str:
        return compute_venv_lock_hash(self)

    def config_to_json(self) -> bytes:
        return config_to_json(self)

    def get_odoo_ci_image_name(self) -> str:
        return self._paths.get_odoo_ci_image_name()

    def get_effective_odoo_build_date(self) -> str:
        return self._loader.get_effective_odoo_build_date()

    def apply_odoo_build_date_to_platform(self) -> None:
        self.odoo_platform_project.apply_build_date(
            self.odoo_build_date,
            str(self.odoo_version),
        )

    def get_platform_sorces(self) -> None:
        self._bind_platform_link()
        self.odoo_platform_project.build_project()
        self.apply_odoo_build_date_to_platform()

    def generate_odoo_conf_docker_data(self) -> None:
        self._odoo_conf.generate_odoo_conf_docker_data()
