"""Prepare-phase context and step definition types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .compose_preview_port import ComposePreviewPort
from .. import constants
from ..compose.generator import ComposeGenerator
from ..compose.service_builder import ComposeServiceBuilder
from ..database.drift import detect_database_drift_for_handle
from ..docker_capabilities import ensure_config_docker_capabilities
from ..extensions.context import ExtensionHostContext
from ..git.deps_lock_manager import DepsLockManager
from ..git.service_sources import (
    apply_materialized_service_sources,
    collect_service_source_paths,
    ensure_service_sources_present,
    materialize_service_sources,
    service_sources_need_materialize_for_view,
)
from ..git.worktree import git_worktree_requested
from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..host.ports import PipelinePorts
from ..plan.core import PlanStep
from ..project_env.links import ProjectLinks
from ..project_env.templates import ProjectTemplates
from ..secrets_providers.fetch import ensure_secrets_source_for_config
from ..symlinks.manager import SymlinkManager

if TYPE_CHECKING:
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
        return self.ports.bootstrap.env_resolver

    def secrets_session(self):
        return self.ports.bootstrap.secrets_session()

    def ensure_secrets_source(self, raw, *, phase: str = "prepare"):
        return ensure_secrets_source_for_config(
            self.ports.bootstrap.config, raw=raw, phase=phase
        )

    def service_sources_need_materialize(self) -> bool:
        return service_sources_need_materialize_for_view(
            manifest_view=self.manifest_view,
            odoo_projects_dir=self.host_ctx.user_env.odoo_projects_dir,
            use_worktree=git_worktree_requested(self.args),
            project_dir=self.host_ctx.project_dir,
            path_to_ssh_key=self.host_ctx.user_env.path_to_ssh_key,
        )

    def run_service_sources_materialize(
        self, *, skip_git: bool, lock_entries: dict
    ) -> None:
        bootstrap = self.ports.bootstrap
        view = self.manifest_view
        if view is None or not view.service_sources:
            SymlinkManager(bootstrap).sync_service_source_project_links({})
            return
        if skip_git:
            ensure_service_sources_present(bootstrap)
            paths = collect_service_source_paths(bootstrap)
        else:
            paths = materialize_service_sources(bootstrap, lock_entries=lock_entries)
        apply_materialized_service_sources(bootstrap, paths)

    def compute_venv_lock_hash(self) -> str:
        return self.ports.bootstrap.compute_venv_lock_hash()

    def rebuild_compose_template(self) -> None:
        self.ports.bootstrap.pd_manager.rebuild_docker_compose_template()

    def build_compose_service(self):
        return ComposeServiceBuilder(self.ports.bootstrap).build()

    def ensure_compose_docker_ready(self, policy) -> None:
        config = self.ports.bootstrap.config
        if policy.skip_compose_cli_probe:
            if not config.runtime.docker_compose_command:
                config.runtime.docker_compose_command = (
                    constants.DEFAULT_DOCKER_COMPOSE_COMMAND
                )
        else:
            ensure_config_docker_capabilities(config)

    def detect_database_drift(self):
        return detect_database_drift_for_handle(self.ports.bootstrap)


@dataclass(frozen=True)
class PrepareStepDef:
    id: str
    description: str
    evaluate: Callable[[PrepareContext], PlanStep]
    execute: Callable[[PrepareContext], None]
