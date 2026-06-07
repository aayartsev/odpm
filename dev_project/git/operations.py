from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from .. import constants
from ..errors import GitError
from ..logging import get_module_logger
from ..inside_docker_app.utils import (
    commit_before_timestamp,
    is_actionable_build_date,
    shallow_since_date,
)
from ..subprocess_runner import CommandResult
from .checkout import CheckoutService
from .clone import RepoCloneService
from .runner import GitRunner

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)


class GitOperations:
    def __init__(self, link: HandleOdooProjectLink) -> None:
        self.link = link
        self._runner = GitRunner(link)
        self._clone = RepoCloneService(link, self._runner)
        self._checkout = CheckoutService(link, self._runner)

    def _build_git_cmd(self, args: list[str]) -> list[str]:
        return self._runner.build_git_cmd(args)

    def _run_git(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        capture: bool = True,
    ) -> CommandResult:
        return self._runner.run_git(args, cwd=cwd, capture=capture)

    def check_project(self) -> None:
        self._clone.check_project()

    def force_clone_repo(self) -> None:
        self._clone.force_clone_repo()

    def clone_repo(self) -> None:
        self._clone.clone_repo()

    def check_repo_url(self, repo_path: str, expected_url: str) -> bool:
        return self._clone.check_repo_url(repo_path, expected_url)

    def resolve_head_sha(self) -> str:
        if not os.path.exists(os.path.join(self.link.project_path, ".git")):
            raise RuntimeError(
                f"Cannot resolve HEAD: not a git repository: {self.link.project_path}"
            )
        result = self._run_git(["rev-parse", "HEAD"])
        commit = result.stdout.strip()
        if result.returncode != 0 or not commit:
            raise RuntimeError(
                f"git rev-parse HEAD failed in {self.link.project_path}"
            )
        return commit

    def _branch_ref(self, branch: str) -> str:
        for ref in (f"origin/{branch}", branch):
            result = self._run_git(["rev-parse", "--verify", ref])
            if result.returncode == 0:
                return ref
        raise RuntimeError(
            f"Branch {branch!r} not found in {self.link.project_path}. "
            "Check odoo_git_link branch or odoo_version."
        )

    def resolve_commit_by_build_date(self, branch: str, build_date: str) -> str:
        before = commit_before_timestamp(build_date)
        ref = self._branch_ref(branch)
        result = self._run_git(["rev-list", "-1", f"--before={before}", ref])
        commit = result.stdout.strip()
        if result.returncode != 0 or not commit:
            raise RuntimeError(
                f"No commit on {ref} before {before} in {self.link.project_path}. "
                "Try a newer build date or check branch name."
            )
        return commit

    def _fetch_history_for_build_date(self, branch: str, build_date: str) -> None:
        since = shallow_since_date(build_date)
        _logger.info(
            "Fetching history for odoo_build_date %s (shallow-since=%s)",
            build_date,
            since,
        )
        result = self._run_git(
            ["fetch", "origin", branch, f"--shallow-since={since}"],
            capture=False,
        )
        if result.returncode == 0:
            return

        step = constants.PLATFORM_BUILD_DATE_FETCH_DEEPEN_STEP
        max_extra = constants.PLATFORM_BUILD_DATE_FETCH_DEEPEN_MAX
        fetched = 0
        while fetched < max_extra:
            _logger.info("Deepening history +%s commits (%s/%s)", step, fetched, max_extra)
            deepen_result = self._run_git(["fetch", "--deepen", str(step)], capture=False)
            if deepen_result.returncode != 0:
                raise RuntimeError(
                    f"git fetch --deepen failed in {self.link.project_path}"
                )
            fetched += step
            try:
                self.resolve_commit_by_build_date(branch, build_date)
                return
            except RuntimeError:
                continue

        raise RuntimeError(
            f"Could not fetch enough history for build date {build_date} "
            f"(deepened {fetched} commits, max {max_extra})."
        )

    def resolve_commit_with_fetch(self, branch: str, build_date: str) -> str:
        try:
            return self.resolve_commit_by_build_date(branch, build_date)
        except RuntimeError:
            pass
        self.link._fetch_history_for_build_date(branch, build_date)
        return self.resolve_commit_by_build_date(branch, build_date)

    def apply_build_date(self, build_date: str, odoo_version: str) -> None:
        if not is_actionable_build_date(build_date):
            return
        if self.link.commit_explicit:
            _logger.warning(
                "odoo_build_date %s ignored: commit is set explicitly in odoo_git_link",
                build_date,
            )
            return
        if self.link.link_type == constants.GITLINK_TYPE_FILE:
            return

        branch = self.link.branch if self.link.branch_explicit else odoo_version
        _logger.info(
            "Resolving odoo_build_date %s on branch %s in %s",
            build_date,
            branch,
            self.link.project_path,
        )
        if os.path.exists(os.path.join(self.link.project_path, ".git")):
            self._checkout.ensure_branch_exists(branch, odoo_version)
        try:
            commit = self.resolve_commit_with_fetch(branch, build_date)
        except (ValueError, RuntimeError) as error:
            message = f"Failed to resolve odoo_build_date {build_date}: {error}"
            _logger.error(message)
            raise GitError(message) from error

        self.link.commit = commit
        self.link.commit_explicit = True
        _logger.info(
            "Resolved odoo_build_date %s to commit %s on branch %s",
            build_date,
            commit[:12],
            branch,
        )

    def checkout_parsed_or_version(self, odoo_version: str) -> None:
        self._checkout.checkout_parsed_or_version(odoo_version)

    def ensure_branch_exists(self, branch_name: str, odoo_version: str) -> None:
        self._checkout.ensure_branch_exists(branch_name, odoo_version)

    def get_odoo_latest_version(self) -> float:
        return self._checkout.get_odoo_latest_version()

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
        self._checkout.checkout(
            branch,
            commit=commit,
            hard=hard,
            clean=clean,
            update=update,
            odoo_version=odoo_version,
            odoo_version_sync=odoo_version_sync,
        )

    def checkout_repository(
        self,
        odoo_version: str,
        *,
        clean_git_repos: bool = False,
        update_git_repos: bool = False,
    ) -> None:
        self._checkout.checkout_repository(
            odoo_version,
            clean_git_repos=clean_git_repos,
            update_git_repos=update_git_repos,
        )

    def switch_to_branch(self, branch_name: str) -> None:
        self._checkout.switch_to_branch(branch_name)
