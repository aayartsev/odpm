"""Manifest v2 ``locks`` block ↔ ``.odpm/deps.lock.json`` conversion."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants
from ..errors import ConfigError
from ..git.deps_lock import (
    DepsLock,
    LockEntry,
    canonical_repo_url,
    sort_lock_entries,
)
from ..translations import _
from .schema import validate_manifest_v2

if TYPE_CHECKING:
    from ..config import Config
    from .reader import ManifestView


class LockSource(str, Enum):
    """Where git lock pins are read from during prepare."""

    DEPS_FILE = "deps_file"
    MANIFEST = "manifest"


def lookup_git_lock_commit(git_locks: dict[str, str], git_link: str) -> str | None:
    """Resolve commit for a manifest/git link against ``locks.git`` keys."""
    link = (git_link or "").strip()
    if not link or not git_locks:
        return None
    if link in git_locks:
        return git_locks[link]
    target = canonical_repo_url(link)
    for key, commit in git_locks.items():
        if canonical_repo_url(key) == target:
            return commit
    return None


def git_locks_map_from_deps_lock(lock: DepsLock) -> dict[str, str]:
    """Build manifest ``locks.git`` url→commit map from deps.lock entries."""
    git_map: dict[str, str] = {}
    for entry in (lock.platform, lock.developing, *lock.dependencies):
        if entry is not None:
            git_map[entry.url] = entry.commit
    return git_map


def normalized_git_lock_commits(git_locks: dict[str, str]) -> dict[str, str]:
    """Map canonical repo URL → commit for manifest or deps.lock git maps."""
    normalized: dict[str, str] = {}
    for key, commit in git_locks.items():
        normalized[canonical_repo_url(key)] = commit
    return normalized


def compare_manifest_and_deps_git_locks(
    manifest_git_locks: dict[str, str],
    deps_lock: DepsLock,
) -> list[str]:
    """Return human-readable per-repo divergences (empty when maps match)."""
    manifest_map = normalized_git_lock_commits(manifest_git_locks)
    deps_map = normalized_git_lock_commits(git_locks_map_from_deps_lock(deps_lock))
    divergences: list[str] = []
    for url in sorted(set(manifest_map) | set(deps_map)):
        manifest_commit = manifest_map.get(url)
        deps_commit = deps_map.get(url)
        if manifest_commit == deps_commit:
            continue
        if manifest_commit and deps_commit:
            divergences.append(
                f"{url}: manifest locks.git has {manifest_commit[:12]}, "
                f"deps.lock.json has {deps_commit[:12]}"
            )
        elif manifest_commit:
            divergences.append(f"{url}: present only in manifest locks.git")
        else:
            divergences.append(f"{url}: present only in deps.lock.json")
    return divergences


def manifest_git_locks_from_view(manifest_view: ManifestView | None) -> dict[str, str]:
    """Return manifest ``locks.git`` map when present on a v2 manifest."""
    if manifest_view is None:
        return {}
    locks = manifest_view.locks or {}
    git_locks = locks.get("git")
    if not isinstance(git_locks, dict):
        return {}
    return {str(key): str(value) for key, value in git_locks.items()}


def manifest_git_locks_from_config(config: Config) -> dict[str, str]:
    """Return manifest ``locks.git`` map when present on a v2 manifest."""
    return manifest_git_locks_from_view(config.bootstrap.manifest_view)


def manifest_locks_from_deps_lock(lock: DepsLock) -> dict[str, Any]:
    """Convert :class:`DepsLock` to manifest v2 ``locks`` object."""
    git_map = git_locks_map_from_deps_lock(lock)
    if not git_map:
        return {}
    return {"git": git_map}


def deps_lock_from_manifest_git_locks(
    git_locks: dict[str, str],
    *,
    platform_git_link: str,
    developing_git_link: str | None,
    dependency_git_links: list[str],
) -> DepsLock:
    """Reconstruct :class:`DepsLock` from manifest ``locks.git`` and manifest links."""

    def entry_for_link(git_link: str) -> LockEntry | None:
        commit = lookup_git_lock_commit(git_locks, git_link)
        if not commit:
            return None
        return LockEntry(url=canonical_repo_url(git_link), commit=commit)

    platform_entry = entry_for_link(platform_git_link)
    if platform_entry is None:
        raise ValueError(
            f"manifest locks.git has no entry for platform link {platform_git_link!r}"
        )

    developing_entry = None
    if developing_git_link:
        developing_entry = entry_for_link(developing_git_link)

    dependency_entries: list[LockEntry] = []
    for dep_link in dependency_git_links:
        entry = entry_for_link(dep_link)
        if entry is not None:
            dependency_entries.append(entry)

    return DepsLock(
        platform=platform_entry,
        developing=developing_entry,
        dependencies=sort_lock_entries(dependency_entries),
    )


def resolve_lock_source_from_view(manifest_view: ManifestView | None) -> LockSource:
    """Prefer manifest ``locks.git`` on v2 manifests; otherwise deps.lock.json."""
    if (
        manifest_view is not None
        and manifest_view.manifest_schema == constants.MANIFEST_SCHEMA_V2
    ):
        locks = manifest_view.locks or {}
        git_locks = locks.get("git")
        if isinstance(git_locks, dict) and git_locks:
            return LockSource.MANIFEST
    return LockSource.DEPS_FILE


def resolve_lock_source(config: Config) -> LockSource:
    """Prefer manifest ``locks.git`` on v2 manifests; otherwise deps.lock.json."""
    return resolve_lock_source_from_view(config.bootstrap.manifest_view)


def developing_git_link_from_config(config: Config) -> str | None:
    developing = config.bootstrap.developing_project
    if developing is None:
        return None
    link = getattr(developing, "project_link", None) or getattr(
        developing, "project_string", None
    )
    if not link:
        return None
    return str(link).strip() or None


def write_manifest_git_locks_from_deps_lock(
    manifest_path: str,
    lock: DepsLock,
) -> bool:
    """Write ``locks.git`` in a v2 manifest from *lock*. Returns True when updated."""
    path = Path(manifest_path)
    if not path.is_file():
        raise ConfigError(
            _("Manifest file not found at {PATH}.").format(PATH=manifest_path)
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(
            _("Manifest at {PATH} is not valid JSON.").format(PATH=manifest_path)
        ) from exc
    if not isinstance(raw, dict):
        raise ConfigError(_("Manifest root must be a JSON object."))
    if raw.get("manifest_schema") != constants.MANIFEST_SCHEMA_V2:
        return False
    git_map = manifest_locks_from_deps_lock(lock).get("git")
    if not isinstance(git_map, dict) or not git_map:
        return False
    locks = raw.get("locks")
    if not isinstance(locks, dict):
        locks = {}
    locks["git"] = git_map
    raw["locks"] = locks
    validate_manifest_v2(raw)
    path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    return True
