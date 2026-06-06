"""Git dependency lock file (.odpm/deps.lock.json) — schema v1 (P8a: platform + seed deps)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .. import constants

DEPS_LOCK_SCHEMA_VERSION = 1
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


@dataclass(frozen=True)
class LockEntry:
    url: str
    commit: str
    branch: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": self.url, "commit": self.commit}
        if self.branch:
            payload["branch"] = self.branch
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LockEntry:
        url = str(data.get("url", "")).strip()
        commit = str(data.get("commit", "")).strip()
        branch = data.get("branch")
        if not url or not commit:
            raise ValueError("lock entry requires url and commit")
        if not _COMMIT_RE.match(commit):
            raise ValueError(f"invalid commit hash: {commit!r}")
        return cls(url=url, commit=commit, branch=str(branch) if branch else None)


@dataclass
class DepsLock:
    schema_version: int = DEPS_LOCK_SCHEMA_VERSION
    generated_at: str = ""
    platform: LockEntry | None = None
    dependencies: list[LockEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if not self.platform:
            raise ValueError("platform entry is required")
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "platform": self.platform.to_dict(),
            "dependencies": [entry.to_dict() for entry in self.dependencies],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DepsLock:
        version = int(data.get("schema_version", 0))
        if version != DEPS_LOCK_SCHEMA_VERSION:
            raise ValueError(f"unsupported deps.lock schema_version: {version}")
        platform_raw = data.get("platform")
        if not isinstance(platform_raw, dict):
            raise ValueError("platform must be an object")
        dependencies_raw = data.get("dependencies", [])
        if not isinstance(dependencies_raw, list):
            raise ValueError("dependencies must be a list")
        return cls(
            schema_version=version,
            generated_at=str(data.get("generated_at", "")),
            platform=LockEntry.from_dict(platform_raw),
            dependencies=[
                LockEntry.from_dict(item)
                for item in dependencies_raw
                if isinstance(item, dict)
            ],
        )


def deps_lock_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.DEPS_LOCK_REL_PATH)


def normalize_repo_url(url: str) -> str:
    """Normalize git URL for lock lookup (first token, no .git suffix)."""
    token = (url or "").strip().split()[0]
    return token.rstrip("/").removesuffix(".git")


def repo_url_for_link(link) -> str:
    raw = link.gitlink or link.project_link or link.project_string
    return normalize_repo_url(raw)


def is_git_repository(project_path: str) -> bool:
    return os.path.isdir(os.path.join(project_path, ".git"))


def snapshot_commit_for_path(project_path: str) -> str:
    """40-char fingerprint for file:// platform trees (no .git directory)."""
    hasher = hashlib.sha256()
    hashed = False
    for rel in ("odoo/release.py", "odoo-bin"):
        path = os.path.join(project_path, rel)
        if os.path.isfile(path):
            with open(path, "rb") as reader:
                hasher.update(rel.encode("utf-8"))
                hasher.update(b"\0")
                hasher.update(reader.read())
            hashed = True
    if not hashed:
        abs_path = os.path.abspath(project_path)
        stat = os.stat(abs_path)
        hasher.update(abs_path.encode("utf-8"))
        hasher.update(str(stat.st_mtime_ns).encode("ascii"))
    return hasher.hexdigest()[:40]


def resolve_lock_commit(link) -> str:
    if link.commit_explicit and link.commit and _COMMIT_RE.match(link.commit):
        return link.commit
    project_path = link.get_project_path()
    if is_git_repository(project_path):
        return link.resolve_head_sha()
    if link.link_type == constants.GITLINK_TYPE_FILE:
        return snapshot_commit_for_path(project_path)
    raise RuntimeError(
        f"Cannot resolve lock commit for {link.project_string!r}: "
        f"not a git repository ({project_path})"
    )


def load_deps_lock(path: str) -> DepsLock | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as reader:
        data = json.load(reader)
    if not isinstance(data, dict):
        raise ValueError("deps.lock.json must be a JSON object")
    return DepsLock.from_dict(data)


def save_deps_lock(path: str, lock: DepsLock) -> None:
    if not lock.generated_at:
        lock.generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = json.dumps(lock.to_dict(), indent=2, sort_keys=True) + "\n"
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as writer:
        writer.write(payload)
    os.replace(tmp_path, path)


def entry_for_url(lock: DepsLock, url: str) -> LockEntry | None:
    normalized = normalize_repo_url(url)
    if lock.platform and normalize_repo_url(lock.platform.url) == normalized:
        return lock.platform
    for entry in lock.dependencies:
        if normalize_repo_url(entry.url) == normalized:
            return entry
    return None


def apply_lock_entry_to_link(link, entry: LockEntry) -> None:
    link.commit = entry.commit
    link.commit_explicit = True
    if entry.branch:
        link.branch = entry.branch
        link.branch_explicit = True
