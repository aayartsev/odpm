"""Read-only host project view built from :class:`Config`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..config.state import (
    AddonLayoutState,
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
)
from ..scenario_policy import ScenarioPolicy
from .cli.args import OdpmCliArgs
from .user_env import CreateUserEnvironment

if TYPE_CHECKING:
    from ..config.config import Config
    from ..manifest.reader import ManifestView


@dataclass(frozen=True)
class HostProjectContext:
    """Stable read-only snapshot of host paths, CLI args, policy, and settings slices."""

    project_dir: str
    program_dir: str
    config_home_dir: str
    policy: ScenarioPolicy
    user_env: CreateUserEnvironment
    arguments: OdpmCliArgs
    user_settings: UserSettingsState
    project_settings: ProjectSettingsState
    docker_layout: DockerLayoutState
    addon_layout: AddonLayoutState
    docker_compose_command: str = ""
    manifest_view: ManifestView | None = None
    repo_odpm_json: str = ""

    @classmethod
    def from_config(
        cls,
        config: Config,
        *,
        arguments: OdpmCliArgs | None = None,
    ) -> HostProjectContext:
        bootstrap = getattr(config, "bootstrap", None)
        manifest_view = (
            bootstrap.manifest_view if bootstrap is not None else None
        )
        repo_odpm_json = (
            bootstrap.repo_odpm_json if bootstrap is not None else ""
        )
        from ..host.runtime import HostRuntimeState  # noqa: PLC0415  # optional

        layout_default = getattr(
            getattr(config, "docker_layout", None),
            "docker_compose_command",
            "",
        )
        if not isinstance(layout_default, str):
            layout_default = ""
        runtime = getattr(config, "runtime", None)
        if isinstance(runtime, HostRuntimeState):
            docker_compose_command = runtime.resolved_docker_compose_command(
                layout_default
            )
        else:
            override = getattr(runtime, "docker_compose_command", None)
            docker_compose_command = (
                override if isinstance(override, str) else layout_default
            )

        return cls(
            project_dir=config.project_dir,
            program_dir=config.program_dir,
            config_home_dir=config.config_home_dir,
            policy=config.policy,
            user_env=config.user_env,
            arguments=arguments if arguments is not None else config.arguments,
            user_settings=config.user_settings,
            project_settings=config.project_settings,
            docker_layout=config.docker_layout,
            addon_layout=config.addon_layout,
            docker_compose_command=docker_compose_command,
            manifest_view=manifest_view,
            repo_odpm_json=repo_odpm_json,
        )

    @property
    def skip_git_update(self) -> bool:
        return bool(self.arguments.no_git_update)

    @property
    def update_lock(self) -> bool:
        return bool(self.arguments.update_lock)

    @property
    def sync_manifest_locks(self) -> bool:
        return bool(self.arguments.sync_manifest_locks)
