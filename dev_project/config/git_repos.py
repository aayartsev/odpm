from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

from ..errors import ConfigError
from ..git import HandleOdooProjectLink
from ..inside_docker_app.logger import get_module_logger

if TYPE_CHECKING:
    from .config import Config

_logger = get_module_logger(__name__)


class GitRepoCoordinator:
    def __init__(self, config: Config) -> None:
        self.config = config

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
        if materialize:
            odoo_project.build_project()
        return odoo_project

    def ensure_git_repos_present(self) -> None:
        missing: list[str] = []
        for label, path in (
            ("platform", self.config.odoo_src_dir),
            ("developing", self.config.developing_project_dir_path),
        ):
            if not path or not os.path.isdir(path):
                missing.append(f"{label}: {path or '<unset>'}")
        if missing:
            message = (
                "--no-git-update requires existing local repository directories: "
                + ", ".join(missing)
            )
            _logger.error(message)
            raise ConfigError(message)

    def materialize_git_repos(self, *, skip_build_date: bool = False) -> None:
        self.config._developing_materializer.materialize_full(self.config)

        self.config.odoo_platform_project.build_project()
        if not skip_build_date:
            self.apply_odoo_build_date_to_platform()

        self.config._paths.apply_developing_project_docker_path()

    def apply_odoo_build_date_to_platform(self) -> None:
        self.config.odoo_platform_project.apply_build_date(
            self.config.odoo_build_date,
            str(self.config.odoo_version),
        )

    def get_platform_sources(self) -> None:
        self.config._bind_platform_link()
        self.config.odoo_platform_project.build_project()
        self.apply_odoo_build_date_to_platform()

    def get_platform_sorces(self) -> None:
        self.get_platform_sources()
