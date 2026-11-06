"""Odoo nightly build-date resolution: commit lookup, history fetch, apply to link."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from ..errors import GitError
from ..logging import get_module_logger
from ..inside_docker_app.utils import (
    commit_before_timestamp,
    is_actionable_build_date,
    shallow_since_date,
)
from .checkout import CheckoutService
from .runner import GitRunner

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)


class BuildDateResolver:
    def __init__(
        self,
        link: HandleOdooProjectLink,
        runner: GitRunner,
        checkout: CheckoutService,
    ) -> None:
        self.link = link
        self._runner = runner
        self._checkout = checkout

    def resolve_head_sha(self) -> str:
        if not os.path.exists(os.path.join(self.link.project_path, ".git")):
            raise RuntimeError(
                f"Cannot resolve HEAD: not a git repository: {self.link.project_path}"
            )
        result = self._runner.run_git(["rev-parse", "HEAD"])
        commit = result.stdout.strip()
        if result.returncode != 0 or not commit:
            raise RuntimeError(
                f"git rev-parse HEAD failed in {self.link.project_path}"
            )
        return commit

    def _branch_ref(self, branch: str) -> str:
        cwd = self._fetch_cwd()
        for ref in (f"origin/{branch}", branch, f"refs/heads/{branch}"):
            result = self._runner.run_git(["rev-parse", "--verify", ref], cwd=cwd)
            if result.returncode == 0:
                return ref
        raise RuntimeError(
            f"Branch {branch!r} not found in {cwd}. "
            "Check odoo_git_link branch or odoo_version."
        )

    def resolve_commit_by_build_date(self, branch: str, build_date: str) -> str:
        before = commit_before_timestamp(build_date)
        cwd = self._fetch_cwd()
        ref = self._branch_ref(branch)
        result = self._runner.run_git(
            ["rev-list", "-1", f"--before={before}", ref],
            cwd=cwd,
        )
        commit = result.stdout.strip()
        if result.returncode != 0 or not commit:
            raise RuntimeError(
                f"No commit on {ref} before {before} in {cwd}. "
                "Try a newer build date or check branch name."
            )
        return commit

    def _fetch_cwd(self) -> str:
        """Prefer bare mirror for deepen when worktree mode is on (ADR-028)."""
        mirror = getattr(self.link, "worktree_mirror", None)
        if mirror and os.path.isdir(mirror):
            return mirror
        return self.link.project_path

    def fetch_history_for_build_date(self, branch: str, build_date: str) -> None:
        since = shallow_since_date(build_date)
        cwd = self._fetch_cwd()
        _logger.info(
            "Fetching history for odoo_build_date %s (shallow-since=%s) in %s",
            build_date,
            since,
            cwd,
        )
        result = self._runner.run_git(
            ["fetch", "origin", branch, f"--shallow-since={since}"],
            cwd=cwd,
            capture=False,
        )
        if result.returncode == 0:
            return

        step = constants.PLATFORM_BUILD_DATE_FETCH_DEEPEN_STEP
        max_extra = constants.PLATFORM_BUILD_DATE_FETCH_DEEPEN_MAX
        fetched = 0
        while fetched < max_extra:
            _logger.info("Deepening history +%s commits (%s/%s)", step, fetched, max_extra)
            deepen_result = self._runner.run_git(
                ["fetch", "--deepen", str(step)],
                cwd=cwd,
                capture=False,
            )
            if deepen_result.returncode != 0:
                raise RuntimeError(
                    f"git fetch --deepen failed in {cwd}"
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
        fetch_cwd = self._fetch_cwd()
        _logger.info(
            "Resolving odoo_build_date %s on branch %s in %s",
            build_date,
            branch,
            fetch_cwd,
        )
        # Prefer bare mirror for branch fetch when worktree mode is on (ADR-028).
        mirror = getattr(self.link, "worktree_mirror", None)
        if mirror and os.path.isdir(mirror):
            self._checkout.ensure_branch_exists(
                branch, odoo_version, cwd=mirror
            )
        elif os.path.exists(os.path.join(self.link.project_path, ".git")):
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
