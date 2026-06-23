from __future__ import annotations

from typing import TYPE_CHECKING

from ..git import HandleOdooProjectLink
from ..git.deps_lock import is_remote_git_link
from ..dependency_resolver import DependencyResolutionResult
from .dependency_materializer import DependencyMaterializer
from ..symlinks import SymlinkManager
from .volume_mapper import VolumeMapper

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment


class ProjectLinks:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env
        self._dependency_resolution: DependencyResolutionResult | None = None

    @property
    def config(self):
        return self.env.config

    @property
    def user_env(self):
        return self.env.user_env

    def map_folders(self) -> None:
        mapper = VolumeMapper(self.env)
        materializer = self._materializer()
        self.env.mapped_folders = mapper.build_base_folders()
        resolution = self._resolve_dependencies()
        self._dependency_resolution = resolution
        materializer.apply_to_config(resolution)
        materialize_deps = not self.config.skip_git_update()
        deps_materialized_during_discovery = (
            materialize_deps and self.config.use_oca_dependencies
        )
        mapper.append_dependency_mounts(
            resolution,
            materialize_deps=materialize_deps,
            skip_materialize=deps_materialized_during_discovery,
        )
        mapper.map_pre_commit_files()

    def _materializer(self) -> DependencyMaterializer:
        return DependencyMaterializer(
            self.config,
            checkout_fn=self.checkout_project,
        )

    def _resolve_dependencies(self) -> DependencyResolutionResult:
        return self._materializer().resolve()

    def _should_checkout_developing(self, lock_manager=None) -> bool:
        developing = self.config.developing_project
        if not is_remote_git_link(developing):
            return False
        if self.config.policy.is_developer():
            return bool(developing.branch_explicit or developing.commit_explicit)
        if lock_manager is not None and lock_manager.is_pinned(developing):
            return True
        return bool(developing.branch_explicit or developing.commit_explicit)

    def checkout_dependencies(self, lock_manager=None) -> None:
        list_for_checkout = [self.config.odoo_platform_project]
        if self._should_checkout_developing(lock_manager):
            list_for_checkout.append(self.config.developing_project)
        list_for_checkout.extend(self.config.dependencies_projects)
        for project in list_for_checkout:
            self.checkout_project(project, lock_manager=lock_manager)

    def checkout_project(
        self, project: HandleOdooProjectLink, *, lock_manager=None
    ) -> None:
        scope = (
            "dependency"
            if project in self.config.dependencies_projects
            else "project"
        )
        project_path = project.project_path
        try:
            update_git_repos = self.config.update_git_repos
            if lock_manager is not None and lock_manager.is_pinned(project):
                update_git_repos = False
            project.checkout_repository(
                self.config.odoo_version,
                clean_git_repos=self.config.clean_git_repos,
                update_git_repos=update_git_repos,
            )
        finally:
            if project_path:
                self.config.ensure_git_repo_symlink(project_path, scope=scope)
                if scope == "project" and project is self.config.developing_project:
                    self.config.ensure_developing_repo_symlinks()

    def update_links(self) -> None:
        SymlinkManager(self.config, host_ctx=self.env.host_ctx).update_links()
