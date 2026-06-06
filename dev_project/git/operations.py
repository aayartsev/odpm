from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING, Optional

from .. import constants, translations
from ..errors import GitError
from ..logging import get_module_logger
from ..inside_docker_app.utils import (
    commit_before_timestamp,
    is_actionable_build_date,
    shallow_since_date,
)
from ..subprocess_runner import CommandResult, run_checked, run_logged

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)


class GitOperations:
    def __init__(self, link: HandleOdooProjectLink) -> None:
        self.link = link

    def _build_git_cmd(self, args: list[str]) -> list[str]:
        if self.link.path_to_ssh_key:
            return [
                "git",
                "-c",
                f"core.sshCommand=ssh -i {self.link.path_to_ssh_key}",
                *args,
            ]
        return ["git", *args]

    def _run_git(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        capture: bool = True,
    ) -> CommandResult:
        cmd = self._build_git_cmd(args)
        workdir = self.link.project_path if cwd is None else cwd
        if not capture:
            _logger.info(
                f"""running command: → git {" ".join(args)} for {self.link.project_string}"""
            )
        return run_checked(cmd, cwd=workdir, capture=capture)

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
                state = self._run_git(
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
            self._build_git_cmd(clone_args),
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
        result = self._run_git(["remote", "get-url", "origin"], cwd=repo_path)
        if result.returncode != 0:
            return False
        actual_url = result.stdout.strip().rstrip(".git").rstrip("/")
        expected_url = expected_url.rstrip(".git").rstrip("/")
        return actual_url == expected_url

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

    def _git_stash(self) -> None:
        self._run_git(["stash"])

    def _git_pull(self) -> None:
        self._run_git(["pull"], capture=False)

    def _git_checkout_ref(self, ref: str) -> None:
        _logger.info(f"Checking out {ref} for {self.link.project_string}")
        self._run_git(["checkout", ref], capture=False)

    def _git_fetch_ref(self, ref: str) -> None:
        verify = self._run_git(["rev-parse", "--verify", ref])
        if verify.returncode == 0:
            return
        self._run_git(["fetch", "--depth", "1", "origin", ref], capture=False)

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
            self.ensure_branch_exists(branch, odoo_version)
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

    def _checkout_version_branch(self, odoo_version: str) -> None:
        self.ensure_branch_exists(odoo_version, odoo_version)
        branch_commit = self._run_git(["rev-parse", "--verify", odoo_version])
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
        current_branches = self._run_git(["branch"])
        if branch_name in current_branches.stdout:
            return
        current_remote_branches = self._run_git(["branch", "-a"])
        if f"origin/{branch_name}" in current_remote_branches.stdout:
            return
        self._run_git(
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
        all_remote_branches = self._run_git(["branch", "-r"])
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
            self._run_git(["clean", "-fd"])
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
