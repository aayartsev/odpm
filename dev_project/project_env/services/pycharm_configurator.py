"""PyCharm run configurations (.run/*.run.xml) for debugger backends."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Literal

from ... import constants
from ...debugger.constants import (
    DEBUGGER_BACKEND_DEBUGPY_LISTEN,
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
)
from ..debug_profile import DebuggerProfile, DebuggerProfileBuilder

if TYPE_CHECKING:
    from ..environment import CreateProjectEnvironment

PycharmRunConfigKind = Literal["dap_attach", "debug_server"]

PYCHARM_RUN_CONFIG_BASENAME = "Odoo Remote Attach"
PYCHARM_DEBUG_SERVER_RUN_CONFIG_BASENAME = "Odoo Debug Server"
PYCHARM_DEBUG_SERVER_UNIT_NAME = "Odoo Debug Server"


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

    @staticmethod
    def run_config_kind(profile: DebuggerProfile) -> PycharmRunConfigKind | None:
        backend = profile.debugger.backend
        if backend == DEBUGGER_BACKEND_DEBUGPY_LISTEN:
            return "dap_attach"
        if backend == DEBUGGER_BACKEND_PYDEVD_CONNECT:
            return "debug_server"
        return None

    @classmethod
    def run_config_basename(cls, profile: DebuggerProfile) -> str | None:
        kind = cls.run_config_kind(profile)
        if kind == "dap_attach":
            return PYCHARM_RUN_CONFIG_BASENAME
        if kind == "debug_server":
            return PYCHARM_DEBUG_SERVER_RUN_CONFIG_BASENAME
        return None

    def run_config_path(self, profile: DebuggerProfile | None = None) -> str:
        profile = profile or self.build_debugger_profile()
        basename = self.run_config_basename(profile)
        if basename is None:
            raise ValueError(
                f"unsupported debugger backend for PyCharm: {profile.debugger.backend!r}"
            )
        return os.path.join(self.get_run_dir_path(), f"{basename}.run.xml")

    def should_generate(self, profile: DebuggerProfile) -> bool:
        return self.run_config_kind(profile) is not None

    def _append_path_mappings(
        self, configuration: ET.Element, profile: DebuggerProfile
    ) -> None:
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

    def build_run_config_xml(self, profile: DebuggerProfile) -> str:
        kind = self.run_config_kind(profile)
        if kind == "dap_attach":
            return self.build_dap_attach_run_config_xml(profile)
        if kind == "debug_server":
            return self.build_debug_server_run_config_xml(profile)
        raise ValueError(
            f"unsupported debugger backend for PyCharm: {profile.debugger.backend!r}"
        )

    def build_dap_attach_run_config_xml(self, profile: DebuggerProfile) -> str:
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
        self._append_path_mappings(configuration, profile)
        ET.SubElement(configuration, "method", {"v": "2"})

        xml_body = ET.tostring(component, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body + "\n"

    def build_debug_server_run_config_xml(self, profile: DebuggerProfile) -> str:
        debugger = profile.debugger
        suspend = bool(getattr(self.env.user_env, "debugger_suspend", False))

        component = ET.Element(
            "component",
            {"name": "ProjectRunConfigurationManager"},
        )
        configuration = ET.SubElement(
            component,
            "configuration",
            {
                "default": "false",
                "name": PYCHARM_DEBUG_SERVER_UNIT_NAME,
                "type": "PyRemoteDebugConfigurationType",
                "factoryName": "Python Debug Server",
            },
        )
        ET.SubElement(
            configuration,
            "option",
            {"name": "PORT", "value": str(debugger.port)},
        )
        ET.SubElement(
            configuration,
            "option",
            {"name": "HOST", "value": debugger.host},
        )
        self._append_path_mappings(configuration, profile)
        ET.SubElement(
            configuration,
            "option",
            {"name": "REDIRECT_OUTPUT", "value": "true"},
        )
        ET.SubElement(
            configuration,
            "option",
            {
                "name": "SUSPEND_AFTER_CONNECT",
                "value": "true" if suspend else "false",
            },
        )
        ET.SubElement(configuration, "method", {"v": "2"})

        xml_body = ET.tostring(component, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body + "\n"

    def update_pycharm_run_configuration(self) -> None:
        profile = self.build_debugger_profile()
        if not self.should_generate(profile):
            return
        path = self.run_config_path(profile)
        content = self.build_run_config_xml(profile)
        with open(path, "w", encoding="utf-8") as outfile:
            outfile.write(content)
