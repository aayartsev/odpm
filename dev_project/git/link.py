from typing import Literal, Optional

from .. import constants
from .discovery import ProjectDiscovery
from .operations import GitOperations
from .parser import LinkParser
from .types import (
    FILE_SYSTEM_MARKER,
    GIT_MARKER,
    HTTP_MARKER,
    SSH_MARKER,
    OdooProjectData,
)


class HandleOdooProjectLink:
    def __init__(
        self,
        project_string: str,
        path_to_ssh_key: str,
        start_dir_to_clone: str,
        system_type: Literal["developing", "platform", "standart"] = "standart",
    ):
        self.is_true = True
        if not project_string:
            self.is_true = False
        self.system_type: Literal["developing", "platform", "standart"] = system_type
        self.project_string = project_string
        self.project_link = ""
        self.gitlink = ""
        self.commit = ""
        self.branch = ""
        self.branch_explicit = False
        self.commit_explicit = False
        self.path_to_ssh_key = path_to_ssh_key
        self.start_dir_to_clone = start_dir_to_clone
        self.dir_to_clone = ""
        self.git_regex = r"git@[a-z._-]*:"
        self.inside_docker_path = ""
        self.is_cloned = False

        self._parser = LinkParser(self)
        self._discovery = ProjectDiscovery(self)
        self._git = GitOperations(self)

        self._parser.parse_project_string()
        self.link_type = self._parser.get_git_link_type()
        self.project_data = self._parser.parse_link_by_type()
        self.project_path = self._parser.get_project_path()
        self._discovery.update_project_type()

    def build_project(self) -> None:
        if self.link_type in [
            constants.GITLINK_TYPE_HTTP,
            constants.GITLINK_TYPE_GIT,
            constants.GITLINK_TYPE_SSH,
        ]:
            self._parser.get_dir_to_clone()
            self._git.check_project()
        if self.link_type in [constants.GITLINK_TYPE_FILE]:
            self.is_cloned = True
        self._discovery.apply_inside_docker_path()

    def get_project_path(self) -> str:
        return self.project_path

    def get_project_type(self) -> Literal["module", "project", "platform"]:
        return self._discovery.get_project_type()

    def update_project_type(self) -> None:
        self._discovery.update_project_type()

    def get_dir_to_clone(self) -> None:
        self._parser.get_dir_to_clone()

    def check_project(self) -> None:
        self._git.check_project()

    def force_clone_repo(self) -> None:
        self._git.force_clone_repo()

    def clone_repo(self) -> None:
        self._git.clone_repo()

    def check_repo_url(self, repo_path: str, expected_url: str) -> bool:
        return self._git.check_repo_url(repo_path, expected_url)

    def resolve_commit_by_build_date(self, branch: str, build_date: str) -> str:
        return self._git.resolve_commit_by_build_date(branch, build_date)

    def resolve_commit_with_fetch(self, branch: str, build_date: str) -> str:
        return self._git.resolve_commit_with_fetch(branch, build_date)

    def apply_build_date(self, build_date: str, odoo_version: str) -> None:
        self._git.apply_build_date(build_date, odoo_version)

    def checkout_repository(
        self,
        odoo_version: str,
        *,
        clean_git_repos: bool = False,
        update_git_repos: bool = False,
    ) -> None:
        self._git.checkout_repository(
            odoo_version,
            clean_git_repos=clean_git_repos,
            update_git_repos=update_git_repos,
        )

    def switch_to_branch(self, branch_name: str) -> None:
        self._git.switch_to_branch(branch_name)

    def checkout(
        self,
        branch: str,
        *,
        commit: Optional[str] = None,
        hard: bool = False,
        clean: bool = False,
        update: bool = False,
        odoo_version: Optional[str] = None,
        odoo_version_sync: bool = False,
    ) -> None:
        self._git.checkout(
            branch,
            commit=commit,
            hard=hard,
            clean=clean,
            update=update,
            odoo_version=odoo_version,
            odoo_version_sync=odoo_version_sync,
        )

    def checkout_parsed_or_version(self, odoo_version: str) -> None:
        self._git.checkout_parsed_or_version(odoo_version)

    def ensure_branch_exists(self, branch_name: str, odoo_version: str) -> None:
        self._git.ensure_branch_exists(branch_name, odoo_version)

    def get_odoo_latest_version(self) -> float:
        return self._git.get_odoo_latest_version()

    def _fetch_history_for_build_date(self, branch: str, build_date: str) -> None:
        self._git._fetch_history_for_build_date(branch, build_date)

    def _run_git(
        self,
        args: list[str],
        *,
        capture: bool = True,
        check: bool = False,
    ):
        return self._git._run_git(args, capture=capture, check=check)

    def __bool__(self) -> bool:
        return self.is_true
