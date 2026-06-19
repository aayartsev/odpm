"""Orchestrate deps.lock.json load, apply, collect, verify, and save."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..errors import PipelineError
from ..logging import get_module_logger
from ..manifest.locks import (
    LockSource,
    deps_lock_from_manifest_git_locks,
    developing_git_link_from_config,
    resolve_lock_source,
)
from .deps_lock import (
    DepsLock,
    LockEntry,
    apply_lock_entry_to_link,
    canonical_repo_url,
    deps_lock_path,
    entry_for_url,
    is_remote_git_link,
    load_deps_lock,
    lock_kind_for_link,
    repo_url_for_link,
    resolve_lock_commit,
    resolved_checkout_commit,
    save_deps_lock,
    sort_lock_entries,
)

if TYPE_CHECKING:
    from ..config import Config
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)


class DepsLockManager:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._path = deps_lock_path(config.project_dir)
        self._lock: DepsLock | None = None
        self._lock_source = LockSource.DEPS_FILE
        self._apply_mode = False
        self._pinned_urls: set[str] = set()
        self._strict = config.policy.is_ci()

    @property
    def lock_source(self) -> LockSource:
        return self._lock_source

    @property
    def apply_mode(self) -> bool:
        return self._apply_mode

    def load(self) -> DepsLock | None:
        self._lock_source = resolve_lock_source(self._config)
        if self._lock_source == LockSource.MANIFEST:
            view = self._config.bootstrap.manifest_view
            locks = (view.locks if view is not None else None) or {}
            git_locks = locks.get("git") or {}
            if not isinstance(git_locks, dict):
                git_locks = {}
            try:
                self._lock = deps_lock_from_manifest_git_locks(
                    git_locks,
                    platform_git_link=self._config.odoo_git_link,
                    developing_git_link=developing_git_link_from_config(self._config),
                    dependency_git_links=list(self._config.dependencies),
                )
            except ValueError as exc:
                message = str(exc)
                if self._strict:
                    _logger.error(message)
                    raise PipelineError(message, exit_code=1) from exc
                _logger.warning(
                    "%s; falling back to .odpm/deps.lock.json",
                    message,
                )
                self._lock_source = LockSource.DEPS_FILE
                self._lock = load_deps_lock(self._path)
            else:
                _logger.info("Loaded git dependency lock from manifest locks.git")
        else:
            self._lock = load_deps_lock(self._path)
        return self._lock

    def has_platform_lock(self) -> bool:
        return self._lock is not None and self._lock.platform is not None

    def enter_apply_mode(self) -> None:
        if self._lock is None:
            return
        self._apply_mode = True
        _logger.info("Applying git dependency lock from %s", self._path)

    def apply_to_platform(self, platform: HandleOdooProjectLink) -> None:
        if not self._apply_mode or self._lock is None or self._lock.platform is None:
            return
        entry = self._lock.platform
        apply_lock_entry_to_link(platform, entry)
        self._pinned_urls.add(canonical_repo_url(entry.url))

    def apply_to_developing(self, developing: HandleOdooProjectLink) -> None:
        if not self._apply_mode or self._lock is None or self._lock.developing is None:
            return
        if self._config.policy.is_developer():
            _logger.info(
                "Skipping developing lock apply in developer scenario; "
                "git state is managed by the developer"
            )
            return
        self._check_stale_developing_entry(developing)
        if not is_remote_git_link(developing):
            return
        entry = self._lock.developing
        apply_lock_entry_to_link(developing, entry)
        self._pinned_urls.add(canonical_repo_url(entry.url))

    def apply_to_dependencies(self, projects: list[HandleOdooProjectLink]) -> None:
        if not self._apply_mode or self._lock is None:
            return
        self._check_seed_coverage()
        self._check_stale_dependency_entries(projects)
        for project in projects:
            project_url = repo_url_for_link(project)
            entry = entry_for_url(self._lock, project_url)
            if entry is None:
                continue
            apply_lock_entry_to_link(project, entry)
            self._pinned_urls.add(canonical_repo_url(entry.url))

    def is_pinned(self, project: HandleOdooProjectLink) -> bool:
        return repo_url_for_link(project) in self._pinned_urls

    def verify_after_checkout(
        self,
        *,
        platform: HandleOdooProjectLink,
        developing: HandleOdooProjectLink,
        dependencies: list[HandleOdooProjectLink],
    ) -> None:
        if not self._apply_mode or self._lock is None:
            return
        self._verify_entry(platform, self._lock.platform, label="platform")
        if (
            self._lock.developing is not None
            and is_remote_git_link(developing)
            and not self._config.policy.is_developer()
        ):
            self._verify_entry(developing, self._lock.developing, label="developing")
        resolved_urls = {repo_url_for_link(project) for project in dependencies}
        for entry in self._lock.dependencies:
            canonical = canonical_repo_url(entry.url)
            if canonical not in resolved_urls:
                continue
            project = self._project_for_url(dependencies, entry.url)
            if project is not None:
                self._verify_entry(project, entry, label=f"dependency {entry.url}")

    def collect_and_save(
        self,
        *,
        developing: HandleOdooProjectLink | None = None,
    ) -> None:
        platform = self._config.odoo_platform_project
        platform_entry = self._entry_from_project(platform)
        dependency_entries = [
            self._entry_from_project(project)
            for project in self._config.dependencies_projects
        ]
        developing_entry = None
        if developing is not None and is_remote_git_link(developing):
            developing_entry = self._entry_from_project(developing)

        lock = DepsLock(
            platform=platform_entry,
            developing=developing_entry,
            dependencies=sort_lock_entries(dependency_entries),
        )
        save_deps_lock(self._path, lock)
        _logger.info("Wrote git dependency lock to %s", self._path)

    def _entry_from_project(self, project: HandleOdooProjectLink) -> LockEntry:
        commit = resolve_lock_commit(project)
        branch = project.branch if project.branch_explicit else None
        return LockEntry(
            url=repo_url_for_link(project),
            commit=commit,
            branch=branch,
            kind=lock_kind_for_link(project),
        )

    def _check_seed_coverage(self) -> None:
        if self._lock is None:
            return
        for seed_url in self._config.seed_dependency_urls():
            if entry_for_url(self._lock, seed_url) is None:
                self._report_issue(
                    f"Seed dependency {seed_url!r} is missing from deps.lock.json; "
                    "run --update-lock and commit the lock file"
                )

    def _check_stale_dependency_entries(
        self, projects: list[HandleOdooProjectLink]
    ) -> None:
        if self._lock is None:
            return
        resolved_urls = {repo_url_for_link(project) for project in projects}
        for entry in self._lock.dependencies:
            canonical = canonical_repo_url(entry.url)
            if canonical not in resolved_urls:
                self._report_issue(
                    f"deps.lock.json lists stale dependency {entry.url!r} "
                    "that is not in the resolved dependency graph; run --update-lock"
                )

    def _check_stale_developing_entry(
        self, developing: HandleOdooProjectLink
    ) -> None:
        if self._lock is None or self._lock.developing is None:
            return
        lock_url = canonical_repo_url(self._lock.developing.url)
        if not is_remote_git_link(developing):
            self._report_issue(
                f"deps.lock.json lists developing {self._lock.developing.url!r} "
                "but the project no longer uses a remote git developing link; "
                "run --update-lock"
            )
            return
        developing_url = repo_url_for_link(developing)
        if developing_url != lock_url:
            self._report_issue(
                f"deps.lock.json lists developing {self._lock.developing.url!r} "
                f"but the project uses {developing.project_link!r}; run --update-lock"
            )

    def _verify_entry(
        self,
        project: HandleOdooProjectLink,
        entry: LockEntry | None,
        *,
        label: str,
    ) -> None:
        if entry is None:
            return
        try:
            current = resolved_checkout_commit(project, entry)
        except RuntimeError as error:
            self._report_issue(f"Cannot verify {label} lock entry: {error}")
            return
        if current != entry.commit:
            self._report_issue(
                f"Lock drift for {label}: deps.lock has {entry.commit[:12]}, "
                f"checkout resolved {current[:12]}"
            )

    @staticmethod
    def _project_for_url(
        projects: list[HandleOdooProjectLink], url: str
    ) -> HandleOdooProjectLink | None:
        target = canonical_repo_url(url)
        for project in projects:
            if repo_url_for_link(project) == target:
                return project
        return None

    def _report_issue(self, message: str) -> None:
        if self._strict:
            _logger.error(message)
            raise PipelineError(message, exit_code=1)
        _logger.warning(message)
