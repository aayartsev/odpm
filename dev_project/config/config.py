from typing import Literal

from ..host_cli.args import OdpmCliArgs

from ..dependency_resolver import NestedOdpmFragment
from ..errors import PipelineError
from ..git import HandleOdooProjectLink
from ..host_user_env import CreateUserEnvironment
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..scenario_policy import ScenarioPolicy
from .bootstrap import bootstrap_config, normalize_project_requirements
from .nested_compatibility import collect_nested_compatibility_issues
from .payload import compute_venv_lock_hash, config_to_json
from .runtime_facade import ConfigRuntimeFacadeMixin
from .state import (
    DOCKER_SLICE_FIELDS,
    PROJECT_SLICE_FIELDS,
    USER_SLICE_FIELDS,
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
    bind_slice_properties,
)
from .types import SubProject

_logger = get_module_logger(__name__)


class Config(ConfigRuntimeFacadeMixin):
    policy: ScenarioPolicy

    def __init__(
        self,
        pd_manager: ProjectDirManager,
        arguments: OdpmCliArgs,
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
    def host_context(self) -> "HostProjectContext":
        from ..host_context import HostProjectContext

        return HostProjectContext.from_config(self)

    def skip_git_update(self) -> bool:
        return bool(self.arguments.no_git_update)

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


bind_slice_properties(Config, "_user", USER_SLICE_FIELDS)
bind_slice_properties(Config, "_project", PROJECT_SLICE_FIELDS)
bind_slice_properties(Config, "_docker", DOCKER_SLICE_FIELDS)
