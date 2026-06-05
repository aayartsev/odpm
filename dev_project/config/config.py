import os
from argparse import Namespace
from typing import Literal

from .. import constants, translations
from ..errors import ConfigError
from ..git import HandleOdooProjectLink
from ..git.developing_repo_materializer import DevelopingRepoMaterializer
from ..host_user_env import CreateUserEnvironment
from ..inside_docker_app.logger import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..protocols import SystemCheckerProtocol
from ..scenario_policy import ScenarioPolicy, is_debugpy_requirement
from ..start_command import ComposeOdooService
from .loader import ConfigLoader
from .odoo_conf import OdooConfBuilder
from .paths import ConfigPaths
from .payload import compute_venv_lock_hash, config_to_json
from .state import (
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
    _slice_property,
    merged_config_dict_view,
    project_settings_from_raw,
    split_config_dict,
    user_settings_from_raw,
    warn_config_dict_access,
)
from .types import SubProject

_logger = get_module_logger(__name__)


class Config:
    policy: ScenarioPolicy

    init_modules = _slice_property("_user", "init_modules")
    update_modules = _slice_property("_user", "update_modules")
    db_creation_data = _slice_property("_user", "db_creation_data")
    update_git_repos = _slice_property("_user", "update_git_repos")
    clean_git_repos = _slice_property("_user", "clean_git_repos")
    check_system = _slice_property("_user", "check_system")
    db_manager_password = _slice_property("_user", "db_manager_password")
    dev_mode = _slice_property("_user", "dev_mode")
    developing_project = _slice_property("_user", "developing_project")
    pre_commit_map_files = _slice_property("_user", "pre_commit_map_files")
    sql_queries = _slice_property("_user", "sql_queries")
    use_oca_dependencies = _slice_property("_user", "use_oca_dependencies")
    create_module_links = _slice_property("_user", "create_module_links")

    odoo_version = _slice_property("_project", "odoo_version")
    python_version = _slice_property("_project", "python_version")
    distro_version = _slice_property("_project", "distro_version")
    distro_name = _slice_property("_project", "distro_name")
    postgres_version = _slice_property("_project", "postgres_version")
    distro_version_codename = _slice_property("_project", "distro_version_codename")
    dependencies = _slice_property("_project", "dependencies")
    requirements_txt = _slice_property("_project", "requirements_txt")
    odoo_build_date = _slice_property("_project", "odoo_build_date")
    odoo_git_link = _slice_property("_project", "odoo_git_link")
    platform_name = _slice_property("_project", "platform_name")
    project_odpm_version = _slice_property("_project", "project_odpm_version")
    arch = _slice_property("_project", "arch")

    dockerfile_template_name = _slice_property("_docker", "dockerfile_template_name")
    project_dockerfile_template_path = _slice_property(
        "_docker", "project_dockerfile_template_path"
    )
    project_dockerignore_template_path = _slice_property(
        "_docker", "project_dockerignore_template_path"
    )
    dependencies_dirs = _slice_property("_docker", "dependencies_dirs")
    dependencies_projects = _slice_property("_docker", "dependencies_projects")
    debugger_path_mappings = _slice_property("_docker", "debugger_path_mappings")
    symlinks_sources = _slice_property("_docker", "symlinks_sources")
    odoo_config_data = _slice_property("_docker", "odoo_config_data")
    odoo_image_name = _slice_property("_docker", "odoo_image_name")
    odoo_ci_image_name = _slice_property("_docker", "odoo_ci_image_name")
    ci_build_context_dir = _slice_property("_docker", "ci_build_context_dir")
    docker_project_dir = _slice_property("_docker", "docker_project_dir")
    docker_dev_project_dir = _slice_property("_docker", "docker_dev_project_dir")
    docker_inside_app = _slice_property("_docker", "docker_inside_app")
    docker_odoo_dir = _slice_property("_docker", "docker_odoo_dir")
    docker_extra_addons = _slice_property("_docker", "docker_extra_addons")
    path_odoo_conf = _slice_property("_docker", "path_odoo_conf")
    docker_path_odoo_conf = _slice_property("_docker", "docker_path_odoo_conf")
    docker_venv_dir = _slice_property("_docker", "docker_venv_dir")
    docker_backups_dir = _slice_property("_docker", "docker_backups_dir")
    docker_temp_tests_dir = _slice_property("_docker", "docker_temp_tests_dir")
    venv_dir = _slice_property("_docker", "venv_dir")
    dir_for_odoo_container_home = _slice_property("_docker", "dir_for_odoo_container_home")
    dependencies_dir = _slice_property("_docker", "dependencies_dir")
    odoo_tests_dir = _slice_property("_docker", "odoo_tests_dir")
    compose_file_version = _slice_property("_docker", "compose_file_version")
    docker_compose_command = _slice_property("_docker", "docker_compose_command")
    docker_odoo_project_dir_path = _slice_property("_docker", "docker_odoo_project_dir_path")
    list_for_symlinks = _slice_property("_docker", "list_for_symlinks")
    docker_dirs_with_addons = _slice_property("_docker", "docker_dirs_with_addons")

    def __init__(
        self,
        pd_manager: ProjectDirManager,
        arguments: Namespace,
        program_dir: str,
        user_env: CreateUserEnvironment,
    ) -> None:
        """Bootstrap host configuration in ordered phases:

        1. Context and user settings (``user_settings.json``).
        2. Developing project link (no clone yet) and optional early clone so
           ``odpm.json`` can be read from a remote git repository.
        3. Project settings from ``odpm.json``.
        4. Platform (Odoo core) link.
        5. Scenario policy, Docker layout, and addon paths.

        Full git clone/update for the prepare phase runs later via
        :meth:`materialize_git_repos` (``OdpmPipeline.prepare_project_files``).
        """
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
        self._raw_user_settings: dict = {}
        self._raw_odpm_json: dict = {}
        self._user_loaded = False
        self._project_loaded = False
        self.repo_odpm_json = ""
        self.dockerfile_path = ""
        self.config_json_loaded = False
        self.compose_service: ComposeOdooService | None = None
        self.start_string = ""
        self.project_dir = self.pd_manager.project_path
        self.config_home_dir = self.pd_manager.home_config_dir
        self.no_log_prefix = False
        self.user_env = user_env
        self.policy = ScenarioPolicy.from_scenario(self.user_env.odpm_scenario)
        self._user = UserSettingsState()
        self._project = ProjectSettingsState()
        self._docker = DockerLayoutState()
        self._loader = ConfigLoader(self)
        self._paths = ConfigPaths(self)
        self._odoo_conf = OdooConfBuilder(self)
        self.postgres_data_local_storage = (
            self._paths.get_postgres_data_local_storage_path()
        )
        self.config_json_content = {}
        self._developing_materializer = DevelopingRepoMaterializer()

    def _load_user_settings(self) -> None:
        self._loader.check_for_config()
        self._loader.get_user_settings_json()
        self._loader.get_user_settings()
        self._user = user_settings_from_raw(
            self._raw_user_settings,
            beautify_module_list=self._loader.beautify_module_list,
        )
        self._user_loaded = True

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
        self._developing_materializer.materialize_for_odpm_json(self)

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

        self._project = project_settings_from_raw(
            self._raw_odpm_json,
            self.arguments,
            odoo_build_date=self._loader.get_effective_odoo_build_date(),
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
        self._project_loaded = True

    def _bind_platform_link(self) -> None:
        self.odoo_platform_project = self.handle_git_link(
            self.odoo_git_link,
            system_type="platform",
            materialize=False,
        )
        self.odoo_src_dir = self.odoo_platform_project.get_project_path()

    def _apply_policy_and_layout(self) -> None:
        original_requirements_txt = list(self.requirements_txt)
        normalized_requirements = self.policy.normalize_requirements(
            self.requirements_txt,
            python_version=self.python_version,
        )
        arch = self._raw_odpm_json.get("arch", constants.ARCH)
        if arch == "auto":
            arch = constants.ARCH

        dockerfile_template_name = (
            f"{self.distro_name}_{self.distro_version.replace('.', '')}_dockerfile"
        )
        project_dockerfile_template_path = os.path.join(
            self.pd_manager.project_path,
            os.path.join(
                constants.PROJECT_SERVICE_DIRECTORY, dockerfile_template_name
            ),
        )
        self._loader.check_file_for_deprecated_words(project_dockerfile_template_path)
        self.pd_manager.rebuild_dockerfile_template(
            docker_template_filename=dockerfile_template_name
        )

        project_dockerignore_template_path = os.path.join(
            self.pd_manager.project_path,
            constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        self.pd_manager.rebuild_dockerignore_template()

        self._project = ProjectSettingsState(
            odoo_version=self.odoo_version,
            python_version=self.python_version,
            distro_version=self.distro_version,
            distro_name=self.distro_name,
            postgres_version=self.postgres_version,
            distro_version_codename=self.distro_version_codename,
            dependencies=self.dependencies,
            requirements_txt=normalized_requirements,
            odoo_build_date=self.odoo_build_date,
            odoo_git_link=self.odoo_git_link,
            platform_name=self.platform_name,
            project_odpm_version=self.project_odpm_version,
            arch=arch,
        )
        self._docker = DockerLayoutState(
            dockerfile_template_name=dockerfile_template_name,
            project_dockerfile_template_path=project_dockerfile_template_path,
            project_dockerignore_template_path=project_dockerignore_template_path,
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

        self._paths.apply_image_names()
        self._paths.apply_docker_layout()
        self._paths.apply_developing_project_docker_path()
        self._odoo_conf.populate_addons_paths()

        self.odoo_config_data = {}
        self._paths.apply_symlink_sources()

    @property
    def config_dict(self) -> dict:
        warn_config_dict_access()
        return merged_config_dict_view(
            self._raw_user_settings,
            self._raw_odpm_json,
            self._user,
            self._project,
            user_loaded=self._user_loaded,
            project_loaded=self._project_loaded,
        )

    @config_dict.setter
    def config_dict(self, value: dict) -> None:
        warn_config_dict_access()
        user_data, odpm_data = split_config_dict(value)
        self._raw_user_settings = user_data
        self._raw_odpm_json = odpm_data

    @property
    def user_settings(self) -> UserSettingsState:
        return self._user

    @property
    def project_settings(self) -> ProjectSettingsState:
        return self._project

    @property
    def docker_layout(self) -> DockerLayoutState:
        return self._docker

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
        self._developing_materializer.materialize_full(self)

        self.odoo_platform_project.build_project()
        self.apply_odoo_build_date_to_platform()

        self._paths.apply_developing_project_docker_path()

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
