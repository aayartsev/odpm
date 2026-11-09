from __future__ import annotations

from typing import TYPE_CHECKING

from .assembly import host_context_from_assembled

if TYPE_CHECKING:
    from ..host.context import HostProjectContext

from ..host.cli.args import OdpmCliArgs
from ..host.runtime import HostRuntimeState

from ..host.user_env import CreateUserEnvironment
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..scenario_policy import ScenarioPolicy
from .bootstrap import bootstrap_config, normalize_project_requirements
from ..secrets_providers.session import SecretsFetchSession
from .transforms.env_substitution import EnvResolver
from .payload import compute_extras_stamp, compute_venv_lock_hash, config_to_json
from .state import (
    AddonLayoutState,
    BootstrapState,
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
    _ensure_bootstrap_state,
    bind_bootstrap_properties,
)
from .types import SubProject

_logger = get_module_logger(__name__)


class AssembledProject:
    policy: ScenarioPolicy

    def __init__(
        self,
        pd_manager: ProjectDirManager,
        arguments: OdpmCliArgs,
        program_dir: str,
        user_env: CreateUserEnvironment,
        *,
        secrets_fetch_session: object | None = None,
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
        self.secrets_fetch_session = secrets_fetch_session or SecretsFetchSession()
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
    def addon_layout(self) -> AddonLayoutState:
        return self._addon_layout

    @property
    def runtime(self) -> HostRuntimeState:
        if not hasattr(self, "_runtime"):
            self._runtime = HostRuntimeState()
        return self._runtime

    @property
    def bootstrap(self) -> BootstrapState:
        return _ensure_bootstrap_state(self)

    @property
    def env_resolver(self) -> EnvResolver:
        return self._env_resolver

    @property
    def host_context(self) -> HostProjectContext:

        return host_context_from_assembled(self)

    def skip_git_update(self) -> bool:
        return bool(self.arguments.no_git_update)

    def seed_dependency_urls(self) -> list[str]:
        """Dependency URLs from ``odpm.json`` before OCA resolution."""
        seeds = self._raw_odpm_json.get("dependencies", [])
        if not isinstance(seeds, list):
            return []
        return [str(url).strip() for url in seeds if url and str(url).strip()]

    def ensure_git_repos_present(self) -> None:
        self._git_repos.ensure_git_repos_present()

    def materialize_git_repos(self, *, skip_build_date: bool = False) -> None:
        self._git_repos.materialize_git_repos(skip_build_date=skip_build_date)

    def check_project_for_subprojects(self, project_path: str) -> list[SubProject]:
        return self._odoo_conf.check_project_for_subprojects(project_path)

    def compute_venv_lock_hash(self) -> str:
        return compute_venv_lock_hash(self)

    def compute_extras_stamp(self) -> str:
        return compute_extras_stamp(self.project_settings.requirements_txt)

    def config_to_json(self) -> bytes:
        return config_to_json(self)


bind_bootstrap_properties(AssembledProject)
