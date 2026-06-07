"""VS Code settings and debugger launch configuration."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from ... import constants, translations
from ..types import DebuggerPathRecord, DebuggerUnit

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

    def build_debugger_path_mappings(self) -> list[DebuggerPathRecord]:
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
            translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )
        vscode_settings_json_path = os.path.join(
            self.get_vscode_dir_path(), "settings.json"
        )
        with open(vscode_settings_json_path, "w") as writer:
            writer.write(content)
