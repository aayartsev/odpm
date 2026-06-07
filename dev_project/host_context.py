"""Read-only host project view built from :class:`Config`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .host_cli.args import OdpmCliArgs
from .host_user_env import CreateUserEnvironment
from .scenario_policy import ScenarioPolicy
from .config.state import (
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
)

if TYPE_CHECKING:
    from .config.config import Config


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

    @classmethod
    def from_config(
        cls,
        config: Config,
        *,
        arguments: OdpmCliArgs | None = None,
    ) -> HostProjectContext:
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
        )

    @property
    def skip_git_update(self) -> bool:
        return bool(self.arguments.no_git_update)

    @property
    def update_lock(self) -> bool:
        return bool(self.arguments.update_lock)
