from argparse import Namespace
from typing import Literal

from ..dependency_resolver import NestedOdpmFragment
from ..errors import PipelineError
from ..git import HandleOdooProjectLink
from ..host_runtime import HostRuntimeState
from ..host_user_env import CreateUserEnvironment
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..scenario_policy import ScenarioPolicy
from ..start_command import ComposeOdooService
from .bootstrap import bootstrap_config, normalize_project_requirements
from .nested_compatibility import collect_nested_compatibility_issues
from .payload import compute_venv_lock_hash, config_to_json
from .state import (
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
    _slice_property,
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
        bootstrap_config(self, pd_manager, arguments, program_dir, user_env)

    def _normalize_project_requirements(self, requirements_txt: list[str]) -> list[str]:
        return normalize_project_requirements(self, requirements_txt)

    @property
    def user_settings(self) -> UserSettingsState:
        return self._user

    @property
    def project_settings(self) -> ProjectSettingsState:
        return self._project

    @property
    def docker_layout(self) -> DockerLayoutState:
        return self._docker

    @property
    def runtime(self) -> HostRuntimeState:
        if not hasattr(self, "_runtime"):
            self._runtime = HostRuntimeState()
        return self._runtime

    @property
    def host_context(self) -> "HostProjectContext":
        from ..host_context import HostProjectContext

        return HostProjectContext.from_config(self)

    @property
    def compose_service(self) -> ComposeOdooService | None:
        return self.runtime.compose_service

    @compose_service.setter
    def compose_service(self, value: ComposeOdooService | None) -> None:
        self.runtime.compose_service = value

    @property
    def container_run_mode(self) -> str:
        return self.runtime.container_run_mode

    @container_run_mode.setter
    def container_run_mode(self, value: str) -> None:
        self.runtime.container_run_mode = value

    @property
    def no_log_prefix(self) -> bool:
        return self.runtime.no_log_prefix

    @no_log_prefix.setter
    def no_log_prefix(self, value: bool) -> None:
        self.runtime.no_log_prefix = value

    @property
    def docker_compose_command(self) -> str:
        return self.runtime.resolved_docker_compose_command(
            self._docker.docker_compose_command
        )

    @docker_compose_command.setter
    def docker_compose_command(self, value: str) -> None:
        self.runtime.docker_compose_command = value

    def skip_git_update(self) -> bool:
        return bool(getattr(self.arguments, "no_git_update", False))

    def seed_dependency_urls(self) -> list[str]:
        """Dependency URLs from ``odpm.json`` before OCA resolution."""
        seeds = self._raw_odpm_json.get("dependencies", [])
        if not isinstance(seeds, list):
            return []
        return [str(url).strip() for url in seeds if url and str(url).strip()]

    def apply_transitive_requirements(
        self,
        transitive_requirements: list[str],
        *,
        nested_fragments: list[NestedOdpmFragment] | None = None,
    ) -> None:
        """Merge transitive Python requirements and validate nested manifest versions."""
        fragments = list(nested_fragments or [])
        for message in collect_nested_compatibility_issues(
            self.odoo_version,
            self.python_version,
            fragments,
        ):
            if self.policy.is_ci():
                _logger.error(message)
                raise PipelineError(message, exit_code=1)
            _logger.warning(message)

        if not transitive_requirements:
            return

        merged = list(self.requirements_txt)
        seen = set(merged)
        for requirement in transitive_requirements:
            text = (requirement or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(text)

        self._project.requirements_txt = self._normalize_project_requirements(merged)

    def ensure_git_repos_present(self) -> None:
        self._git_repos.ensure_git_repos_present()

    def materialize_git_repos(self, *, skip_build_date: bool = False) -> None:
        self._git_repos.materialize_git_repos(skip_build_date=skip_build_date)

    def check_project_for_subprojects(self, project_path: str) -> list[SubProject]:
        return self._odoo_conf.check_project_for_subprojects(project_path)

    def handle_git_link(
        self,
        gitlink: str,
        system_type: Literal["developing", "platform", "standart"] = "standart",
        *,
        materialize: bool = False,
    ) -> HandleOdooProjectLink:
        return self._git_repos.handle_git_link(
            gitlink,
            system_type=system_type,
            materialize=materialize,
        )

    def compute_venv_lock_hash(self) -> str:
        return compute_venv_lock_hash(self)

    def config_to_json(self) -> bytes:
        return config_to_json(self)

    def generate_odoo_conf_docker_data(self) -> None:
        self._odoo_conf.generate_odoo_conf_docker_data()
