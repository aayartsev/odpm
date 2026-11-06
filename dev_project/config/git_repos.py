from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

from ..errors import ConfigError
from ..git import HandleOdooProjectLink
from ..git.worktree import (
    bind_link_to_worktree_layout,
    configure_link_worktree_context,
    git_worktree_requested,
    is_git_work_tree,
    tenant_id_from_project_dir,
)
from ..logging import get_module_logger

if TYPE_CHECKING:
    from .config import Config
    from .paths import ConfigPaths

_logger = get_module_logger(__name__)


class GitRepoCoordinator:
    def __init__(
        self,
        config: Config,
        *,
        paths: ConfigPaths,
    ) -> None:
        self.config = config
        self._paths = paths

    def _maybe_enable_worktree(self, link: HandleOdooProjectLink) -> None:
        arguments = getattr(self.config, "arguments", None)
        if not git_worktree_requested(arguments):
            return
        project_dir = getattr(self.config, "project_dir", None)
        if not project_dir:
            return
        tenant = tenant_id_from_project_dir(project_dir)
        skip = False
        skip_fn = getattr(self.config, "skip_git_update", None)
        if callable(skip_fn):
            skip = bool(skip_fn())
        configure_link_worktree_context(
            link,
            tenant=tenant,
            skip_git_update=skip,
        )

    def handle_git_link(
        self,
        gitlink: str,
        system_type: Literal["developing", "platform", "standart"] = "standart",
        *,
        materialize: bool = False,
    ) -> HandleOdooProjectLink:
        odoo_project = HandleOdooProjectLink(
            gitlink,
            self.config.user_env.path_to_ssh_key,
            self.config.user_env.odoo_projects_dir,
            system_type=system_type,
        )
        self._maybe_enable_worktree(odoo_project)
        if materialize:
            odoo_project.build_project()
        return odoo_project

    def _refresh_config_paths_from_links(self) -> None:
        platform = getattr(self.config, "odoo_platform_project", None)
        if (
            platform is not None
            and getattr(platform, "worktree_mode", False) is True
        ):
            path = bind_link_to_worktree_layout(platform)
            if path:
                self.config.odoo_src_dir = path
        developing = getattr(self.config, "developing_project", None)
        if (
            developing is not None
            and getattr(developing, "worktree_mode", False) is True
        ):
            path = bind_link_to_worktree_layout(developing)
            if path:
                self.config.developing_project_dir_path = path

    @staticmethod
    def _is_real_git_link(link) -> bool:
        return bool(
            link is not None
            and not isinstance(link, str)
            and getattr(link, "link_type", None)
        )

    def ensure_git_repos_present(self) -> None:
        platform = getattr(self.config, "odoo_platform_project", None)
        developing = getattr(self.config, "developing_project", None)
        if self._is_real_git_link(platform):
            self._maybe_enable_worktree(platform)
        if self._is_real_git_link(developing):
            self._maybe_enable_worktree(developing)
        self._refresh_config_paths_from_links()

        missing: list[str] = []
        for label, path, link in (
            ("platform", self.config.odoo_src_dir, platform),
            ("developing", self.config.developing_project_dir_path, developing),
        ):
            if not isinstance(path, str) or not path or not os.path.isdir(path):
                missing.append(f"{label}: {path or '<unset>'}")
                continue
            if (
                self._is_real_git_link(link)
                and getattr(link, "worktree_mode", False) is True
                and not is_git_work_tree(path)
            ):
                missing.append(f"{label}: {path} (not a git worktree)")
        if missing:
            message = (
                "--no-git-update requires existing local repository directories: "
                + ", ".join(missing)
            )
            _logger.error(message)
            raise ConfigError(message)

    def materialize_git_repos(self, *, skip_build_date: bool = False) -> None:
        self._maybe_enable_worktree(self.config.developing_project)
        self._maybe_enable_worktree(self.config.odoo_platform_project)
        self.config._developing_materializer.materialize_full(self.config)

        try:
            self.config.odoo_platform_project.build_project()
            if not skip_build_date:
                self.apply_odoo_build_date_to_platform()
        finally:
            platform_path = self.config.odoo_platform_project.project_path
            self.config.odoo_src_dir = platform_path
            self.config.ensure_git_repo_symlink(platform_path, scope="project")

        self._paths.apply_developing_project_docker_path()
        if self.config.developing_project_dir_path:
            self.config.ensure_developing_repo_symlinks()

    def apply_odoo_build_date_to_platform(self) -> None:
        self.config.odoo_platform_project.apply_build_date(
            self.config.odoo_build_date,
            str(self.config.odoo_version),
        )
