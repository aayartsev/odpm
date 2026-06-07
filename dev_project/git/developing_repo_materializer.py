"""Clone/update developing project repo during Config bootstrap and pipeline prepare."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Protocol

from .. import constants
from .link import HandleOdooProjectLink

if TYPE_CHECKING:
    from ..host_cli.args import OdpmCliArgs


class DevelopingRepoConfig(Protocol):
    project_dir: str
    developing_project_dir_path: str
    developing_project: HandleOdooProjectLink
    arguments: OdpmCliArgs

    def skip_git_update(self) -> bool: ...


class DevelopingRepoMaterializer:
    """Tracks and performs developing-repo clone/update in two lifecycle stages."""

    def __init__(self) -> None:
        self._developing_repo_materialized = False

    @property
    def developing_repo_materialized(self) -> bool:
        return self._developing_repo_materialized

    @staticmethod
    def _is_remote_git_link(link: HandleOdooProjectLink) -> bool:
        return link.link_type in (
            constants.GITLINK_TYPE_HTTP,
            constants.GITLINK_TYPE_GIT,
            constants.GITLINK_TYPE_SSH,
        )

    def materialize_for_odpm_json(self, config: DevelopingRepoConfig) -> bool:
        """Clone developing repo before reading odpm.json when it lives in git.

        Returns True when the repository was cloned or updated in this call.
        """
        if not self._is_remote_git_link(config.developing_project):
            return False
        if config.skip_git_update():
            return False
        repo_odpm_json = os.path.join(
            config.developing_project.project_path,
            constants.PROJECT_CONFIG_FILE_NAME,
        )
        project_odpm_json = os.path.join(
            config.project_dir,
            constants.PROJECT_CONFIG_FILE_NAME,
        )
        if os.path.exists(repo_odpm_json) or os.path.exists(project_odpm_json):
            return False
        self._build_developing(config)
        return True

    def materialize_full(self, config: DevelopingRepoConfig) -> None:
        """Ensure developing repo exists and is on the requested branch."""
        if not self._developing_repo_materialized:
            self._build_developing(config)

    def _build_developing(self, config: DevelopingRepoConfig) -> None:
        config.developing_project.build_project()
        if config.arguments.branch and isinstance(config.arguments.branch, str):
            config.developing_project.switch_to_branch(config.arguments.branch)
        config.developing_project_dir_path = config.developing_project.project_path
        self._developing_repo_materialized = True
