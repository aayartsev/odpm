from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..subprocess_runner import CommandResult
from .build_date import BuildDateResolver
from .checkout import CheckoutService
from .clone import RepoCloneService
from .runner import GitRunner

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink


class GitOperations:
    def __init__(self, link: HandleOdooProjectLink) -> None:
        self.link = link
        self._runner = GitRunner(link)
        self._clone = RepoCloneService(link, self._runner)
        self._checkout = CheckoutService(link, self._runner)
        self._build_date = BuildDateResolver(link, self._runner, self._checkout)

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
        return self._build_date.resolve_head_sha()

    def resolve_commit_by_build_date(self, branch: str, build_date: str) -> str:
        return self._build_date.resolve_commit_by_build_date(branch, build_date)

    def _fetch_history_for_build_date(self, branch: str, build_date: str) -> None:
        self._build_date.fetch_history_for_build_date(branch, build_date)

    def resolve_commit_with_fetch(self, branch: str, build_date: str) -> str:
        return self._build_date.resolve_commit_with_fetch(branch, build_date)

    def apply_build_date(self, build_date: str, odoo_version: str) -> None:
        self._build_date.apply_build_date(build_date, odoo_version)

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
