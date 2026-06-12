"""VS Code settings and debugger launch configuration."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from ... import constants
from ...translations import _
from ..debug_profile import DebuggerProfile, DebuggerProfileBuilder
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

    def build_debugger_profile(self) -> DebuggerProfile:
        return DebuggerProfileBuilder(self.env).build()

    def build_debugger_path_mappings(self) -> list[DebuggerPathRecord]:
        return self.build_debugger_profile().to_vscode_path_mappings()

    def _debugger_unit_from_profile(self, profile: DebuggerProfile) -> DebuggerUnit:
        debugger = profile.debugger
        return DebuggerUnit(
            name=debugger.name,
            type="python",
            request="attach",
            port=debugger.port,
            host=debugger.host,
            pathMappings=profile.to_vscode_path_mappings(),
        )

    def update_vscode_debugger_launcher(self) -> None:
        profile = self.build_debugger_profile()
        self.config.debugger_path_mappings = profile.to_vscode_path_mappings()

        launch_json = os.path.join(self.get_vscode_dir_path(), "launch.json")
        if not os.path.exists(launch_json):
            content = {"configurations": []}
        else:
            with open(launch_json, "r") as open_file:
                content = json.load(open_file)
        debugger_unit = self._debugger_unit_from_profile(profile)
        debugger_unit_exists = False
        for index, existing_unit in enumerate(content["configurations"]):
            if existing_unit["name"] == constants.DEBUGGER_UNIT_NAME:
                content["configurations"][index] = debugger_unit
                debugger_unit_exists = True
        if not debugger_unit_exists:
            content["configurations"].append(debugger_unit)
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
