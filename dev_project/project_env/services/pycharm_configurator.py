"""PyCharm Attach to DAP run configuration (.run/*.run.xml)."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from ... import constants
from ...debugger.constants import DEBUGGER_BACKEND_DEBUGPY_LISTEN
from ..debug_profile import DebuggerProfile, DebuggerProfileBuilder

if TYPE_CHECKING:
    from ..environment import CreateProjectEnvironment

PYCHARM_RUN_CONFIG_BASENAME = "Odoo Remote Attach"


class PycharmConfigurator:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def build_debugger_profile(self) -> DebuggerProfile:
        return DebuggerProfileBuilder(self.env).build()

    def get_run_dir_path(self) -> str:
        run_dir = os.path.join(self.config.project_dir, ".run")
        if not os.path.exists(run_dir):
            os.mkdir(run_dir)
        return run_dir

    def run_config_path(self) -> str:
        return os.path.join(
            self.get_run_dir_path(),
            f"{PYCHARM_RUN_CONFIG_BASENAME}.run.xml",
        )

    def should_generate(self, profile: DebuggerProfile) -> bool:
        return profile.debugger.backend == DEBUGGER_BACKEND_DEBUGPY_LISTEN

    def build_run_config_xml(self, profile: DebuggerProfile) -> str:
        debugger = profile.debugger
        remote_address = f"{debugger.host}:{debugger.port}"

        component = ET.Element(
            "component",
            {"name": "ProjectRunConfigurationManager"},
        )
        configuration = ET.SubElement(
            component,
            "configuration",
            {
                "default": "false",
                "name": constants.DEBUGGER_UNIT_NAME,
                "type": "PythonDapAttachConfiguration",
            },
        )
        ET.SubElement(
            configuration,
            "option",
            {"name": "remoteAddress", "value": remote_address},
        )

        path_mappings = ET.SubElement(configuration, "PathMappingSettings")
        mappings_option = ET.SubElement(
            path_mappings,
            "option",
            {"name": "pathMappings"},
        )
        mappings_list = ET.SubElement(mappings_option, "list")
        for mapping in profile.path_mappings:
            ET.SubElement(
                mappings_list,
                "mapping",
                {
                    "local-root": mapping.local,
                    "remote-root": mapping.remote,
                },
            )

        ET.SubElement(configuration, "method", {"v": "2"})

        xml_body = ET.tostring(component, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body + "\n"

    def update_pycharm_run_configuration(self) -> None:
        profile = self.build_debugger_profile()
        if not self.should_generate(profile):
            return
        path = self.run_config_path()
        content = self.build_run_config_xml(profile)
        with open(path, "w", encoding="utf-8") as outfile:
            outfile.write(content)
