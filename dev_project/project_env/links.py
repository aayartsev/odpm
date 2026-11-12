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
    def user_env(self):
        return self.env.user_env

    def materialize_dependencies(self) -> None:
        """Resolve dependency URLs and clone/update dependency git repos."""
        materializer = self._materializer()
        resolution = self._resolve_dependencies()
        self._dependency_resolution = resolution
        materializer.apply_to_config(resolution)
        host_ctx = self.env.host_ctx
        bootstrap = self.env.bootstrap
        if host_ctx.skip_git_update:
            return
        # OCA discovery already clones while walking transitive URLs; avoid a
        # second materialize pass. Non-OCA seed URLs still need an explicit clone.
        already_during_discovery = bool(
            host_ctx.user_settings.use_oca_dependencies
        )
        for dependency_string in resolution.urls:
            dependency_project = bootstrap.handle_git_link(
                dependency_string,
                materialize=not already_during_discovery,
            )
            try:
                if already_during_discovery and not dependency_project.is_cloned:
                    dependency_project.build_project()
            finally:
                if dependency_project.project_path:
                    bootstrap.ensure_git_repo_symlink(
                        dependency_project.project_path,
                        scope="dependency",
                    )

    def map_folders(self) -> None:
        """Build docker volume mapping; never clones or walks OCA discovery.

        Prepare runs :meth:`materialize_dependencies` first (full resolve + clone).
        Standalone callers (plan compose preview, tests) map seed ``dependencies``
        URLs already on ``config`` — no git clone side effects.
        """
        mapper = VolumeMapper(self.env)
        self.env.mapped_folders = mapper.build_base_folders()
        if self._dependency_resolution is None:
            resolution = DependencyResolutionResult(
                urls=list(self.env.host_ctx.project_settings.dependencies or []),
                nested_fragments=[],
            )
            self._dependency_resolution = resolution
        else:
            resolution = self._dependency_resolution
        mapper.append_dependency_mounts(
            resolution,
            materialize_deps=False,
            skip_materialize=False,
        )
        mapper.map_pre_commit_files()

    def _materializer(self) -> DependencyMaterializer:
        return DependencyMaterializer(
            self.env.bootstrap,
            checkout_fn=self.checkout_project,
        )

    def _resolve_dependencies(self) -> DependencyResolutionResult:
        return self._materializer().resolve()

    def _should_checkout_developing(self, lock_manager=None) -> bool:
        developing = self.env.bootstrap.developing_project
        if not is_remote_git_link(developing):
            return False
        if self.env.host_ctx.policy.is_developer():
            return bool(developing.branch_explicit or developing.commit_explicit)
        if lock_manager is not None and lock_manager.is_pinned(developing):
            return True
        return bool(developing.branch_explicit or developing.commit_explicit)

    def checkout_dependencies(
        self, lock_manager=None, *, skip_platform: bool = False
    ) -> None:
        bootstrap = self.env.bootstrap
        list_for_checkout = []
        if not skip_platform:
            list_for_checkout.append(bootstrap.odoo_platform_project)
        if self._should_checkout_developing(lock_manager):
            list_for_checkout.append(bootstrap.developing_project)
        list_for_checkout.extend(self.env.host_ctx.docker_layout.dependencies_projects)
        for project in list_for_checkout:
            self.checkout_project(project, lock_manager=lock_manager)

    def checkout_project(
        self, project: HandleOdooProjectLink, *, lock_manager=None
    ) -> None:
        host_ctx = self.env.host_ctx
        bootstrap = self.env.bootstrap
        scope = (
            "dependency"
            if project in host_ctx.docker_layout.dependencies_projects
            else "project"
        )
        try:
            update_git_repos = host_ctx.user_settings.update_git_repos
            if lock_manager is not None and lock_manager.is_pinned(project):
                update_git_repos = False
            project.checkout_repository(
                host_ctx.project_settings.odoo_version,
                clean_git_repos=host_ctx.user_settings.clean_git_repos,
                update_git_repos=update_git_repos,
            )
        finally:
            project_path = project.project_path
            if project is bootstrap.odoo_platform_project and project_path:
                bootstrap.odoo_src_dir = project_path
            if project is bootstrap.developing_project and project_path:
                bootstrap.developing_project_dir_path = project_path
            if project_path:
                bootstrap.ensure_git_repo_symlink(project_path, scope=scope)
                if scope == "project" and project is bootstrap.developing_project:
                    bootstrap.ensure_developing_repo_symlinks()

    def update_links(self) -> None:
        SymlinkManager(
            self.env.bootstrap,
            host_ctx=self.env.host_ctx,
        ).update_links()
