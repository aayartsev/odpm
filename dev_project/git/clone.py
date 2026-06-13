"""Git repository clone lifecycle: check, force re-clone, clone, URL verification."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from .. import constants
from ..errors import GitError
from ..logging import get_module_logger
from ..subprocess_runner import run_logged
from .runner import GitRunner

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)


class RepoCloneService:
    def __init__(self, link: HandleOdooProjectLink, runner: GitRunner) -> None:
        self.link = link
        self._runner = runner

    def check_project(self) -> None:
        inside_work_tree = False
        repo_is_same = False
        project_dir_name = os.path.basename(self.link.project_path)
        new_destination = os.path.join(
            self.link.dir_to_clone, f"new_project_{project_dir_name}"
        )
        if (
            self.link.link_type == constants.GITLINK_TYPE_HTTP
            and ".git" not in self.link.gitlink
        ):
            if os.path.exists(new_destination):
                self.link.project_path = new_destination
        if os.path.exists(self.link.project_path):
            if os.path.exists(os.path.join(self.link.project_path, ".git")):
                state = self._runner.run_git(
                    ["rev-parse", "--is-inside-work-tree"],
                    cwd=self.link.project_path,
                )
                inside_work_tree = state.returncode == 0 and "true" in state.stdout
                if inside_work_tree:
                    repo_is_same = self.check_repo_url(
                        self.link.project_path,
                        self.link.gitlink or self.link.project_link,
                    )
        if not inside_work_tree or not repo_is_same:
            self.force_clone_repo()
        else:
            self.link.is_cloned = True
        if (
            project_dir_name in ["odoo"]
            and not os.path.exists(new_destination)
            and self.link.system_type != "platform"
        ):
            os.rename(self.link.project_path, new_destination)
            self.link.project_path = new_destination

    def force_clone_repo(self) -> None:
        try:
            shutil.rmtree(self.link.project_path)
        except FileNotFoundError:
            pass
        if not os.path.exists(self.link.dir_to_clone):
            os.makedirs(self.link.dir_to_clone)
        self.clone_repo()

    def clone_repo(self) -> None:
        if self.link.system_type != "platform":
            clone_args = ["clone", self.link.gitlink]
        else:
            clone_args = [
                "clone",
                "--depth",
                str(constants.PLATFORM_GIT_CLONE_DEPTH),
            ]
            if self.link.branch_explicit and not self.link.commit_explicit:
                clone_args.extend(["-b", self.link.branch])
            clone_args.append(self.link.gitlink)

        returncode = run_logged(
            self._runner.build_git_cmd(clone_args),
            cwd=self.link.dir_to_clone,
        )

        if returncode != 0:
            message = (
                f"git clone failed for {self.link.gitlink!r} "
                f"(exit code {returncode})"
            )
            _logger.error(message)
            raise GitError(message)

        self.link.is_cloned = True

    def check_repo_url(self, repo_path: str, expected_url: str) -> bool:
        result = self._runner.run_git(["remote", "get-url", "origin"], cwd=repo_path)
        if result.returncode != 0:
            return False
        actual_url = result.stdout.strip().rstrip(".git").rstrip("/")
        expected_url = expected_url.rstrip(".git").rstrip("/")
        return actual_url == expected_url
