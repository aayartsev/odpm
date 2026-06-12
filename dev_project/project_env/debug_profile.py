"""IDE-neutral debugger profile (.odpm/runtime/debug-profile.json) — schema v1."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .. import constants
from .types import DebuggerPathRecord, SymlinksSources

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

DEBUG_PROFILE_SCHEMA_VERSION = 1
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

    def to_dict(self) -> dict[str, Any]:
        return {
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
        return cls(protocol=protocol, host=host, port=port_raw, name=name)


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
        if version != DEBUG_PROFILE_SCHEMA_VERSION:
            raise ValueError(f"unsupported debug profile schema_version: {version}")
        debugger_raw = data.get("debugger")
        if not isinstance(debugger_raw, dict):
            raise ValueError("debugger must be an object")
        mappings_raw = data.get("path_mappings", [])
        if not isinstance(mappings_raw, list):
            raise ValueError("path_mappings must be a list")
        return cls(
            schema_version=version,
            debugger=DebuggerConnection.from_dict(debugger_raw),
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
        return DebuggerProfile(
            debugger=DebuggerConnection(
                protocol=DEBUGGER_PROTOCOL_DEBUGPY,
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
        backups = os.path.abspath(self.env.user_env.backups)
        mappings: list[DebuggerPathMapping] = []
        for mapped_folder in self.env.mapped_folders:
            local_root = os.path.abspath(mapped_folder.local)
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
            if isinstance(entry, SymlinksSources):
                add(entry.link_path, entry.source_path)
            else:
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
            abs_source = os.path.abspath(source_path)
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
