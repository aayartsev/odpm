"""IDE-neutral debugger profile (.odpm/runtime/debug-profile.json) — schema v1."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants
from ..debugger.backends import get_backend
from ..debugger.constants import (
    DEBUGGER_DIRECTION_ATTACH,
    DEBUGGER_DIRECTION_CONNECT,
    DEFAULT_DEBUGGER_BACKEND,
)
from .types import DebuggerPathRecord

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment


def _normalize_local_path(path: str) -> str:
    return os.path.realpath(path)


def debug_profile_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_DEBUG_PROFILE_REL_PATH)


def write_debug_profile_to_path(env: CreateProjectEnvironment, path: str) -> str:
    profile = DebuggerProfileBuilder(env).build()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = json.dumps(profile.to_dict(), ensure_ascii=False, indent=4) + "\n"
    Path(path).write_text(payload, encoding="utf-8")
    return path


def write_debug_profile(env: CreateProjectEnvironment) -> str:
    from ..config.payload import ensure_runtime_dir_gitignore

    project_dir = env.config.project_dir
    ensure_runtime_dir_gitignore(project_dir)
    return write_debug_profile_to_path(env, debug_profile_path(project_dir))

DEBUG_PROFILE_SCHEMA_VERSION = 2
DEBUG_PROFILE_SCHEMA_VERSION_V1 = 1
DEBUGGER_PROTOCOL_DEBUGPY = "debugpy"


@dataclass(frozen=True)
class DebuggerPathMapping:
    local: str
    remote: str

    def to_dict(self) -> dict[str, str]:
        return {"local": self.local, "remote": self.remote}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebuggerPathMapping:
        local = str(data.get("local", "")).strip()
        remote = str(data.get("remote", "")).strip()
        if not local or not remote:
            raise ValueError("path mapping requires local and remote")
        return cls(local=local, remote=remote)


@dataclass(frozen=True)
class DebuggerConnection:
    protocol: str
    host: str
    port: int
    name: str
    backend: str = DEFAULT_DEBUGGER_BACKEND
    direction: str = DEBUGGER_DIRECTION_ATTACH

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "direction": self.direction,
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebuggerConnection:
        protocol = str(data.get("protocol", "")).strip()
        host = str(data.get("host", "")).strip()
        name = str(data.get("name", "")).strip()
        port_raw = data.get("port")
        if not protocol or not host or not name:
            raise ValueError("debugger connection requires protocol, host, and name")
        if not isinstance(port_raw, int) or isinstance(port_raw, bool):
            raise ValueError("debugger connection port must be an integer")
        backend = str(data.get("backend", DEFAULT_DEBUGGER_BACKEND)).strip()
        direction = str(data.get("direction", DEBUGGER_DIRECTION_ATTACH)).strip()
        return cls(
            protocol=protocol,
            host=host,
            port=port_raw,
            name=name,
            backend=backend,
            direction=direction,
        )


@dataclass
class DebuggerProfile:
    debugger: DebuggerConnection
    path_mappings: list[DebuggerPathMapping] = field(default_factory=list)
    schema_version: int = DEBUG_PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "debugger": self.debugger.to_dict(),
            "path_mappings": [mapping.to_dict() for mapping in self.path_mappings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebuggerProfile:
        version = int(data.get("schema_version", 0))
        if version not in (DEBUG_PROFILE_SCHEMA_VERSION_V1, DEBUG_PROFILE_SCHEMA_VERSION):
            raise ValueError(f"unsupported debug profile schema_version: {version}")
        debugger_raw = data.get("debugger")
        if not isinstance(debugger_raw, dict):
            raise ValueError("debugger must be an object")
        debugger = DebuggerConnection.from_dict(debugger_raw)
        if version == DEBUG_PROFILE_SCHEMA_VERSION_V1:
            debugger = DebuggerConnection(
                protocol=debugger.protocol,
                host=debugger.host,
                port=debugger.port,
                name=debugger.name,
                backend=DEFAULT_DEBUGGER_BACKEND,
                direction=DEBUGGER_DIRECTION_ATTACH,
            )
            version = DEBUG_PROFILE_SCHEMA_VERSION
        mappings_raw = data.get("path_mappings", [])
        if not isinstance(mappings_raw, list):
            raise ValueError("path_mappings must be a list")
        return cls(
            schema_version=version,
            debugger=debugger,
            path_mappings=[
                DebuggerPathMapping.from_dict(item)
                for item in mappings_raw
                if isinstance(item, dict)
            ],
        )

    def to_vscode_path_mappings(self) -> list[DebuggerPathRecord]:
        return [
            DebuggerPathRecord(localRoot=mapping.local, remoteRoot=mapping.remote)
            for mapping in self.path_mappings
        ]


class DebuggerProfileBuilder:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def build(self) -> DebuggerProfile:
        port = self.env.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT
        backend_id = self.env.user_env.debugger_backend
        backend = get_backend(backend_id)
        direction = (
            DEBUGGER_DIRECTION_ATTACH
            if backend.direction == "listen"
            else DEBUGGER_DIRECTION_CONNECT
        )
        return DebuggerProfile(
            debugger=DebuggerConnection(
                backend=backend_id,
                direction=direction,
                protocol=backend.protocol,
                host="localhost",
                port=int(port),
                name=constants.DEBUGGER_UNIT_NAME,
            ),
            path_mappings=self.build_path_mappings(),
        )

    def build_path_mappings(self) -> list[DebuggerPathMapping]:
        canonical = self._canonical_volume_mappings()
        return canonical + self._symlink_alias_mappings(canonical)

    def _canonical_volume_mappings(self) -> list[DebuggerPathMapping]:
        backups = _normalize_local_path(self.env.user_env.backups)
        mappings: list[DebuggerPathMapping] = []
        for mapped_folder in self.env.mapped_folders:
            local_root = _normalize_local_path(mapped_folder.local)
            if local_root == backups:
                continue
            mappings.append(
                DebuggerPathMapping(
                    local=local_root,
                    remote=mapped_folder.docker,
                )
            )
        return mappings

    def _remote_root_by_local_path(
        self, mappings: list[DebuggerPathMapping]
    ) -> dict[str, str]:
        return {mapping.local: mapping.remote for mapping in mappings}

    def _symlink_candidates(self) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        seen_pairs: set[tuple[str, str]] = set()

        def add(link_path: str, source_path: str) -> None:
            pair = (link_path, source_path)
            if pair in seen_pairs:
                return
            seen_pairs.add(pair)
            candidates.append(pair)

        for entry in self.config.symlinks_sources:
            add(entry.link_path, entry.source_path)

        for scan_dir in (
            self.config.project_dir,
            self.config.dependencies_dir,
        ):
            if not os.path.isdir(scan_dir):
                continue
            for name in os.listdir(scan_dir):
                link_path = os.path.join(scan_dir, name)
                if not os.path.islink(link_path):
                    continue
                add(link_path, os.path.realpath(link_path))

        return candidates

    def _symlink_alias_mappings(
        self, canonical_mappings: list[DebuggerPathMapping]
    ) -> list[DebuggerPathMapping]:
        remote_by_local = self._remote_root_by_local_path(canonical_mappings)
        canonical_locals = set(remote_by_local)
        aliases: list[DebuggerPathMapping] = []
        seen: set[tuple[str, str]] = set()

        for link_path, source_path in self._symlink_candidates():
            abs_link = os.path.abspath(link_path)
            abs_source = _normalize_local_path(source_path)
            if abs_link == abs_source or abs_link in canonical_locals:
                continue
            remote_root = remote_by_local.get(abs_source)
            if remote_root is None:
                continue
            pair = (abs_link, remote_root)
            if pair in seen:
                continue
            seen.add(pair)
            aliases.append(DebuggerPathMapping(local=abs_link, remote=remote_root))

        aliases.sort(key=lambda mapping: len(mapping.local), reverse=True)
        return aliases
