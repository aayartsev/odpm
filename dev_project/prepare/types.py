"""Prepare-phase context and step definition types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .compose_preview_port import ComposePreviewPort
from ..compose.generator import ComposeGenerator
from ..compose.service_builder import ComposeServiceBuilder
from ..database.drift import detect_database_drift_for_config
from ..extensions.context import ExtensionHostContext
from ..git.deps_lock_manager import DepsLockManager
from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..host.ports import PipelinePorts
from ..plan.core import PlanStep
from ..project_env.links import ProjectLinks
from ..project_env.templates import ProjectTemplates

if TYPE_CHECKING:
    from ..config import Config
    from ..config.git_repos import GitRepoCoordinator
    from ..manifest.reader import ManifestView
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
        """Execute-only bootstrap config; evaluate should use host_ctx / ports."""
        return self.ports.bootstrap.config

    @property
    def compose_preview(self) -> ComposePreviewPort:
        return ComposePreviewPort(self.ports.bootstrap)

    def extension_host(self) -> ExtensionHostContext:
        return ExtensionHostContext.from_host(
            self.host_ctx,
            repo_odpm_json=self.host_ctx.repo_odpm_json,
            manifest_view=self.manifest_view,
        )

    @property
    def git_repos(self) -> GitRepoCoordinator:
        return self.ports.bootstrap.git_repos

    @property
    def manifest_view(self) -> ManifestView | None:
        return self.ports.bootstrap.manifest_view

    @property
    def env_resolver(self):
        return self.ports.bootstrap.config.env_resolver

    def compute_venv_lock_hash(self) -> str:
        return self.ports.bootstrap.compute_venv_lock_hash()

    def rebuild_compose_template(self) -> None:
        self.ports.bootstrap.config.pd_manager.rebuild_docker_compose_template()

    def build_compose_service(self):
        return ComposeServiceBuilder(self.ports.bootstrap.config).build()

    def detect_database_drift(self):
        return detect_database_drift_for_config(self.ports.bootstrap.config)


@dataclass(frozen=True)
class PrepareStepDef:
    id: str
    description: str
    evaluate: Callable[[PrepareContext], PlanStep]
    execute: Callable[[PrepareContext], None]
