"""Prepare-phase context and step definition types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..compose.generator import ComposeGenerator
from ..git.deps_lock_manager import DepsLockManager
from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..host.ports import PipelinePorts
from ..plan import PlanStep
from ..project_env.links import ProjectLinks
from ..project_env.templates import ProjectTemplates

if TYPE_CHECKING:
    from ..config import Config
    from ..config.git_repos import GitRepoCoordinator
    from ..extensions.context import ExtensionHostContext
    from ..project_env import CreateProjectEnvironment
    from ..protocols import SystemCheckerProtocol


@dataclass
class PrepareContext:
    ports: PipelinePorts
    project_env: CreateProjectEnvironment
    templates: ProjectTemplates
    compose_generator: ComposeGenerator
    links: ProjectLinks
    system_checker: SystemCheckerProtocol
    args: OdpmCliArgs
    host_ctx: HostProjectContext
    lock_manager: DepsLockManager | None = None

    @property
    def config(self) -> Config:
        return self.ports.bootstrap.config

    def extension_host(self) -> ExtensionHostContext:
        from ..extensions.context import ExtensionHostContext

        return ExtensionHostContext.from_config(self.config)

    @property
    def git_repos(self) -> GitRepoCoordinator:
        return self.config._git_repos

    @property
    def manifest_view(self):
        return self.config.bootstrap.manifest_view

    def compute_venv_lock_hash(self) -> str:
        return self.config.compute_venv_lock_hash()

    def runtime_preview_cache_config(self) -> Config:
        """Config handle used only for plan runtime preview disk cache."""
        return self.config

    def plan_runtime_config_preview_text(self) -> str | None:
        from ..plan.compose_preview import preview_runtime_config_text

        return preview_runtime_config_text(self.config)

    def plan_compose_start_command_changed(self) -> bool:
        from ..plan.compose_preview import compose_start_command_changed

        return compose_start_command_changed(self.config)

    def plan_preview_compose_service(self):
        from ..plan.compose_preview import preview_compose_service

        return preview_compose_service(self.config)

    def rebuild_compose_template(self) -> None:
        self.config.pd_manager.rebuild_docker_compose_template()

    def build_compose_service(self):
        from ..compose.service_builder import ComposeServiceBuilder

        return ComposeServiceBuilder(self.config).build()

    def detect_database_drift(self):
        from ..database.drift import detect_database_drift_for_config

        return detect_database_drift_for_config(self.config)


@dataclass(frozen=True)
class PrepareStepDef:
    id: str
    description: str
    evaluate: Callable[[PrepareContext], PlanStep]
    execute: Callable[[PrepareContext], None]
