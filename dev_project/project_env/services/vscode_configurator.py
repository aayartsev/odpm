"""VS Code settings and debugger launch configuration."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from ... import constants
from ...translations import _
from ..types import DebuggerPathRecord, DebuggerUnit, SymlinksSources

if TYPE_CHECKING:
    from ..environment import CreateProjectEnvironment


class VscodeConfigurator:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def get_vscode_dir_path(self) -> str:
        vscode_dir = os.path.join(self.config.project_dir, ".vscode")
        if not os.path.exists(vscode_dir):
            os.mkdir(vscode_dir)
        return vscode_dir

    def _canonical_volume_mappings(self) -> list[DebuggerPathRecord]:
        backups = os.path.abspath(self.env.user_env.backups)
        mappings: list[DebuggerPathRecord] = []
        for mapped_folder in self.env.mapped_folders:
            local_root = os.path.abspath(mapped_folder.local)
            if local_root == backups:
                continue
            mappings.append(
                DebuggerPathRecord(
                    localRoot=local_root,
                    remoteRoot=mapped_folder.docker,
                )
            )
        return mappings

    def _remote_root_by_local_path(
        self, mappings: list[DebuggerPathRecord]
    ) -> dict[str, str]:
        return {record["localRoot"]: record["remoteRoot"] for record in mappings}

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
        self, canonical_mappings: list[DebuggerPathRecord]
    ) -> list[DebuggerPathRecord]:
        remote_by_local = self._remote_root_by_local_path(canonical_mappings)
        canonical_locals = set(remote_by_local)
        aliases: list[DebuggerPathRecord] = []
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
            aliases.append(
                DebuggerPathRecord(
                    localRoot=abs_link,
                    remoteRoot=remote_root,
                )
            )

        aliases.sort(key=lambda record: len(record["localRoot"]), reverse=True)
        return aliases

    def build_debugger_path_mappings(self) -> list[DebuggerPathRecord]:
        canonical = self._canonical_volume_mappings()
        return canonical + self._symlink_alias_mappings(canonical)

    def update_vscode_debugger_launcher(self) -> None:
        self.config.debugger_path_mappings = self.build_debugger_path_mappings()

        launch_json = os.path.join(self.get_vscode_dir_path(), "launch.json")
        if not os.path.exists(launch_json):
            content = {"configurations": []}
        else:
            with open(launch_json, "r") as open_file:
                content = json.load(open_file)
        debugger_unit_exists = False
        port = self.env.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT
        odoo_debugger_uint = DebuggerUnit(
            name=constants.DEBUGGER_UNIT_NAME,
            type="python",
            request="attach",
            port=int(port),
            host="localhost",
            pathMappings=self.config.debugger_path_mappings,
        )
        for index, debugger_unit in enumerate(content["configurations"]):
            if debugger_unit["name"] == constants.DEBUGGER_UNIT_NAME:
                content["configurations"][index] = odoo_debugger_uint
                debugger_unit_exists = True
        if not debugger_unit_exists:
            content["configurations"].append(
                DebuggerUnit(
                    name=constants.DEBUGGER_UNIT_NAME,
                    type="python",
                    request="attach",
                    port=self.env.user_env.debugger_port
                    or constants.DEBUGGER_DEFAULT_PORT,
                    host="localhost",
                    pathMappings=self.config.debugger_path_mappings,
                )
            )
        with open(launch_json, "w") as outfile:
            json.dump(content, outfile, indent=4)

    def generate_vscode_settings_json(self) -> None:
        vscode_settings_json_template_path = os.path.join(
            self.config.project_dir, constants.PROJECT_VSCODE_SETTINGS_TEMPLATE
        )
        with open(vscode_settings_json_template_path) as reader:
            lines = reader.readlines()
        content = "".join(lines[1:]).replace(
            "{PYTHON_VERSION}",
            self.config.python_version,
        )
        content = content.replace(
            _('If you want drop this file to default values, just delete it'),
            _('Do not change this file, its content is generating automatically'),
        )
        vscode_settings_json_path = os.path.join(
            self.get_vscode_dir_path(), "settings.json"
        )
        with open(vscode_settings_json_path, "w") as writer:
            writer.write(content)
