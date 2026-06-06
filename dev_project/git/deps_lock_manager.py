"""Orchestrate deps.lock.json load, apply, collect, and save."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import constants
from ..inside_docker_app.logger import get_module_logger
from .deps_lock import (
    DepsLock,
    LockEntry,
    apply_lock_entry_to_link,
    deps_lock_path,
    entry_for_url,
    load_deps_lock,
    normalize_repo_url,
    repo_url_for_link,
    resolve_lock_commit,
    save_deps_lock,
    snapshot_commit_for_path,
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
        self._apply_mode = False
        self._pinned_urls: set[str] = set()

    @property
    def apply_mode(self) -> bool:
        return self._apply_mode

    def load(self) -> DepsLock | None:
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
        if platform.link_type == constants.GITLINK_TYPE_FILE:
            current = snapshot_commit_for_path(platform.project_path)
            if current != entry.commit:
                _logger.warning(
                    "Platform tree fingerprint differs from deps.lock "
                    "(expected %s, current %s)",
                    entry.commit[:12],
                    current[:12],
                )
        apply_lock_entry_to_link(platform, entry)
        self._pinned_urls.add(normalize_repo_url(entry.url))

    def apply_to_seed_dependencies(self, projects: list[HandleOdooProjectLink]) -> None:
        if not self._apply_mode or self._lock is None:
            return
        seed_urls = {
            normalize_repo_url(url) for url in self._config.dependencies if url
        }
        for project in projects:
            project_url = repo_url_for_link(project)
            if project_url not in seed_urls:
                continue
            entry = entry_for_url(self._lock, project_url)
            if entry is None:
                continue
            apply_lock_entry_to_link(project, entry)
            self._pinned_urls.add(normalize_repo_url(entry.url))

    def is_pinned(self, project: HandleOdooProjectLink) -> bool:
        return repo_url_for_link(project) in self._pinned_urls

    def collect_and_save(self) -> None:
        platform = self._config.odoo_platform_project
        platform_entry = self._entry_from_project(platform)
        seed_urls = [
            url for url in self._config.dependencies if url and url.strip()
        ]
        seed_normalized = {normalize_repo_url(url) for url in seed_urls}
        dependency_entries: list[LockEntry] = []
        for project in self._config.dependencies_projects:
            project_url = repo_url_for_link(project)
            if project_url not in seed_normalized:
                continue
            dependency_entries.append(self._entry_from_project(project))

        lock = DepsLock(
            platform=platform_entry,
            dependencies=dependency_entries,
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
        )
