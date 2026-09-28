"""Git dependency lock file (.odpm/deps.lock.json) — schema v1."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse

from .. import constants

DEPS_LOCK_SCHEMA_VERSION = 1
LOCK_KIND_GIT = "git"
LOCK_KIND_FILE = "file"
LockKind = Literal["git", "file"]

_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_SSH_GIT_RE = re.compile(r"^git@([^:]+):(.+)$")


@dataclass(frozen=True)
class LockEntry:
    url: str
    commit: str
    branch: str | None = None
    kind: LockKind = LOCK_KIND_GIT

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": self.url, "commit": self.commit}
        if self.branch:
            payload["branch"] = self.branch
        if self.kind != LOCK_KIND_GIT:
            payload["kind"] = self.kind
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
        kind_raw = data.get("kind")
        if kind_raw is None and url.startswith("file://"):
            kind: LockKind = LOCK_KIND_FILE
        elif kind_raw is None:
            kind = LOCK_KIND_GIT
        else:
            kind = str(kind_raw)
            if kind not in (LOCK_KIND_GIT, LOCK_KIND_FILE):
                raise ValueError(f"unsupported lock entry kind: {kind!r}")
        return cls(
            url=url,
            commit=commit,
            branch=str(branch) if branch else None,
            kind=kind,
        )


@dataclass
class DepsLock:
    schema_version: int = DEPS_LOCK_SCHEMA_VERSION
    generated_at: str = ""
    platform: LockEntry | None = None
    developing: LockEntry | None = None
    dependencies: list[LockEntry] = field(default_factory=list)
    service_sources: dict[str, LockEntry] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        if not self.platform:
            raise ValueError("platform entry is required")
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "platform": self.platform.to_dict(),
            "dependencies": [entry.to_dict() for entry in self.dependencies],
        }
        if self.developing is not None:
            payload["developing"] = self.developing.to_dict()
        if self.service_sources:
            payload["service_sources"] = {
                name: self.service_sources[name].to_dict()
                for name in sorted(self.service_sources)
            }
        return payload

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
        developing_raw = data.get("developing")
        developing = (
            LockEntry.from_dict(developing_raw)
            if isinstance(developing_raw, dict)
            else None
        )
        service_sources_raw = data.get("service_sources", {})
        service_sources: dict[str, LockEntry] = {}
        if isinstance(service_sources_raw, dict):
            for name, raw_entry in service_sources_raw.items():
                if isinstance(raw_entry, dict):
                    service_sources[str(name)] = LockEntry.from_dict(raw_entry)
        return cls(
            schema_version=version,
            generated_at=str(data.get("generated_at", "")),
            platform=LockEntry.from_dict(platform_raw),
            developing=developing,
            dependencies=[
                LockEntry.from_dict(item)
                for item in dependencies_raw
                if isinstance(item, dict)
            ],
            service_sources=service_sources,
        )


def deps_lock_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.DEPS_LOCK_REL_PATH)


def normalize_repo_url(url: str) -> str:
    """Normalize git URL token (first word, no .git suffix)."""
    token = (url or "").strip().split()[0]
    return token.rstrip("/").removesuffix(".git")


def canonical_repo_url(url: str) -> str:
    """Canonical URL for lock storage and lookup."""
    normalized = normalize_repo_url(url)
    if normalized.startswith("file://"):
        return normalized.rstrip("/")

    ssh_match = _SSH_GIT_RE.match(normalized)
    if ssh_match:
        host, path = ssh_match.groups()
        return f"https://{host.lower()}/{path.lstrip('/').rstrip('/')}"

    if normalized.startswith("http://"):
        normalized = "https://" + normalized[len("http://") :]
    if normalized.startswith("https://"):
        parsed = urlparse(normalized)
        return f"https://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"

    return normalized


def repo_url_for_link(link) -> str:
    raw = link.gitlink or link.project_link or link.project_string
    return canonical_repo_url(raw)


def lock_kind_for_link(link) -> LockKind:
    if link.link_type == constants.GITLINK_TYPE_FILE:
        return LOCK_KIND_FILE
    return LOCK_KIND_GIT


def is_git_repository(project_path: str) -> bool:
    return os.path.isdir(os.path.join(project_path, ".git"))


def is_remote_git_link(link) -> bool:
    return bool(link) and getattr(link, "is_true", True) and link.link_type in (
        constants.GITLINK_TYPE_HTTP,
        constants.GITLINK_TYPE_GIT,
        constants.GITLINK_TYPE_SSH,
    )


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


def resolved_checkout_commit(link, entry: LockEntry | None = None) -> str:
    """Current commit/fingerprint after checkout (ignores explicit pin on link)."""
    project_path = link.get_project_path()
    if is_git_repository(project_path):
        return link.resolve_head_sha()
    if entry is not None and entry.kind == LOCK_KIND_FILE:
        return snapshot_commit_for_path(project_path)
    if link.link_type == constants.GITLINK_TYPE_FILE:
        return snapshot_commit_for_path(project_path)
    raise RuntimeError(
        f"Cannot resolve checkout commit for {link.project_string!r}: "
        f"not a git repository ({project_path})"
    )


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


def sort_lock_entries(entries: list[LockEntry]) -> list[LockEntry]:
    return sorted(entries, key=lambda entry: canonical_repo_url(entry.url))


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
    normalized = canonical_repo_url(url)
    if lock.platform and canonical_repo_url(lock.platform.url) == normalized:
        return lock.platform
    if lock.developing and canonical_repo_url(lock.developing.url) == normalized:
        return lock.developing
    for entry in lock.dependencies:
        if canonical_repo_url(entry.url) == normalized:
            return entry
    return None


def entry_for_service_source(lock: DepsLock, name: str) -> LockEntry | None:
    return lock.service_sources.get(name)


def apply_lock_entry_to_link(link, entry: LockEntry) -> None:
    link.commit = entry.commit
    link.commit_explicit = True
    if entry.branch:
        link.branch = entry.branch
        link.branch_explicit = True
