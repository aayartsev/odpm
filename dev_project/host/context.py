"""Read-only host project view built by ``config.assembly`` factories."""

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

    @property
    def skip_git_update(self) -> bool:
        return bool(self.arguments.no_git_update)

    @property
    def update_lock(self) -> bool:
        return bool(self.arguments.update_lock)

    @property
    def sync_manifest_locks(self) -> bool:
        return bool(self.arguments.sync_manifest_locks)
