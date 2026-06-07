"""Git checkout orchestration: branch sync, version resolution, hard/clean updates."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from .. import constants, translations
from ..errors import GitError
from ..logging import get_module_logger
from .runner import GitRunner

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)


class CheckoutService:
    def __init__(self, link: HandleOdooProjectLink, runner: GitRunner) -> None:
        self.link = link
        self._runner = runner

    def _git_stash(self) -> None:
        self._runner.run_git(["stash"])

    def _git_pull(self) -> None:
        self._runner.run_git(["pull"], capture=False)

    def _git_checkout_ref(self, ref: str) -> None:
        _logger.info(f"Checking out {ref} for {self.link.project_string}")
        self._runner.run_git(["checkout", ref], capture=False)

    def _git_fetch_ref(self, ref: str) -> None:
        verify = self._runner.run_git(["rev-parse", "--verify", ref])
        if verify.returncode == 0:
            return
        self._runner.run_git(["fetch", "--depth", "1", "origin", ref], capture=False)

    def _checkout_version_branch(self, odoo_version: str) -> None:
        self.ensure_branch_exists(odoo_version, odoo_version)
        branch_commit = self._runner.run_git(["rev-parse", "--verify", odoo_version])
        branch_commit_string = branch_commit.stdout.strip() or branch_commit.stderr.strip()
        if branch_commit.returncode != 0 or "fatal" in branch_commit_string:
            newest_version = self.get_odoo_latest_version()
            self._git_checkout_ref(str(newest_version))
            self._git_pull()
            newest_version = self.get_odoo_latest_version()
            if str(newest_version) == odoo_version:
                self._git_checkout_ref(str(newest_version))
            else:
                message = (
                    f"Version {odoo_version} not exists in git repository "
                    f"{self.link.project_path}"
                )
                _logger.error(message)
                raise GitError(message)
        else:
            self._git_checkout_ref(odoo_version)

    def checkout_parsed_or_version(self, odoo_version: str) -> None:
        if self.link.link_type == constants.GITLINK_TYPE_FILE:
            return
        if not os.path.exists(os.path.join(self.link.project_path, ".git")):
            return

        if self.link.commit_explicit:
            self._git_fetch_ref(self.link.commit)
            self._git_checkout_ref(self.link.commit)
        elif self.link.branch_explicit:
            self.ensure_branch_exists(self.link.branch, odoo_version)
            self._git_checkout_ref(self.link.branch)
        else:
            self._checkout_version_branch(odoo_version)

    def ensure_branch_exists(self, branch_name: str, odoo_version: str) -> None:
        current_branches = self._runner.run_git(["branch"])
        if branch_name in current_branches.stdout:
            return
        current_remote_branches = self._runner.run_git(["branch", "-a"])
        if f"origin/{branch_name}" in current_remote_branches.stdout:
            return
        self._runner.run_git(
            [
                "fetch",
                "--depth",
                "1",
                "origin",
                f"{branch_name}:{branch_name}",
            ],
            capture=False,
        )

    def get_odoo_latest_version(self) -> float:
        all_remote_branches = self._runner.run_git(["branch", "-r"])
        list_of_versions = []
        for branch_name in all_remote_branches.stdout.strip().split("\n"):
            if not branch_name.strip():
                continue
            try:
                branch_version = float(branch_name.split("/")[1])
                list_of_versions.append(branch_version)
            except ValueError:
                continue
        if not list_of_versions:
            message = (
                f"No numeric version branches found in {self.link.project_path}. "
                "Set an explicit branch or commit in the project git link."
            )
            _logger.error(message)
            raise GitError(message)
        return sorted(list_of_versions)[-1]

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
        if hard:
            self._git_stash()
            self._runner.run_git(["clean", "-fd"])
            self._git_pull()
            self._git_checkout_ref(commit or branch)
            return

        odoo_version = odoo_version or branch

        if clean:
            self._git_stash()

        if odoo_version_sync:
            self.checkout_parsed_or_version(odoo_version)

        if update and not self.link.commit_explicit:
            self._git_pull()

    def checkout_repository(
        self,
        odoo_version: str,
        *,
        clean_git_repos: bool = False,
        update_git_repos: bool = False,
    ) -> None:
        self.checkout(
            odoo_version,
            clean=clean_git_repos,
            update=update_git_repos,
            odoo_version=odoo_version,
            odoo_version_sync=True,
        )

    def switch_to_branch(self, branch_name: str) -> None:
        _logger.info(
            translations.get_translation(translations.SWITCHING_TO_BRANCH).format(
                PROJECT_NAME=self.link.project_string,
                BRANCH_NAME=branch_name,
            )
        )
        self.checkout(branch_name, hard=True)
