"""Tests for PyCharm run configuration generation."""

from __future__ import annotations

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.debugger.constants import DEBUGGER_BACKEND_PYDEVD_CONNECT
from dev_project.project_env.services.pycharm_configurator import (
    PYCHARM_DEBUG_SERVER_RUN_CONFIG_BASENAME,
    PYCHARM_DEBUG_SERVER_UNIT_NAME,
    PycharmConfigurator,
)
from dev_project.project_env.types import MappedPath

from tests.debug_profile_test_helpers import make_debugger_env_mock


class PycharmConfiguratorTests(unittest.TestCase):
    def test_build_run_config_xml_contains_dap_attach_fields(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)
            env = make_debugger_env_mock(
                project_dir=project_dir,
                mapped_folders=[
                    MappedPath(local=odoo_src, docker="/home/odoo/odoo"),
                ],
            )
            configurator = PycharmConfigurator(env)
            profile = configurator.build_debugger_profile()
            xml_text = configurator.build_dap_attach_run_config_xml(profile)

            root = ET.fromstring(xml_text)
            configuration = root.find("configuration")
            self.assertIsNotNone(configuration)
            assert configuration is not None
            self.assertEqual(
                configuration.get("type"),
                "PythonDapAttachConfiguration",
            )
            self.assertEqual(
                configuration.get("name"),
                constants.DEBUGGER_UNIT_NAME,
            )

            remote_address = configuration.find("./option[@name='remoteAddress']")
            self.assertIsNotNone(remote_address)
            assert remote_address is not None
            self.assertEqual(remote_address.get("value"), "localhost:5678")

            mapping = configuration.find(
                "./PathMappingSettings/option[@name='pathMappings']/list/mapping"
            )
            self.assertIsNotNone(mapping)
            assert mapping is not None
            self.assertEqual(
                mapping.get("local-root"),
                os.path.realpath(odoo_src),
            )
            self.assertEqual(mapping.get("remote-root"), "/home/odoo/odoo")

    def test_build_debug_server_run_config_xml_contains_pydevd_fields(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)
            env = make_debugger_env_mock(
                project_dir=project_dir,
                mapped_folders=[
                    MappedPath(local=odoo_src, docker="/home/odoo/odoo"),
                ],
            )
            env.user_env.debugger_backend = DEBUGGER_BACKEND_PYDEVD_CONNECT
            env.user_env.debugger_suspend = True
            configurator = PycharmConfigurator(env)
            profile = configurator.build_debugger_profile()
            xml_text = configurator.build_debug_server_run_config_xml(profile)

            root = ET.fromstring(xml_text)
            configuration = root.find("configuration")
            self.assertIsNotNone(configuration)
            assert configuration is not None
            self.assertEqual(
                configuration.get("type"),
                "PyRemoteDebugConfigurationType",
            )
            self.assertEqual(
                configuration.get("factoryName"),
                "Python Debug Server",
            )
            self.assertEqual(
                configuration.get("name"),
                PYCHARM_DEBUG_SERVER_UNIT_NAME,
            )

            host = configuration.find("./option[@name='HOST']")
            port = configuration.find("./option[@name='PORT']")
            suspend = configuration.find("./option[@name='SUSPEND_AFTER_CONNECT']")
            redirect = configuration.find("./option[@name='REDIRECT_OUTPUT']")
            self.assertIsNotNone(host)
            self.assertIsNotNone(port)
            self.assertIsNotNone(suspend)
            self.assertIsNotNone(redirect)
            assert host is not None
            assert port is not None
            assert suspend is not None
            assert redirect is not None
            self.assertEqual(host.get("value"), "localhost")
            self.assertEqual(port.get("value"), "5678")
            self.assertEqual(suspend.get("value"), "true")
            self.assertEqual(redirect.get("value"), "true")

            mapping = configuration.find(
                "./PathMappingSettings/option[@name='pathMappings']/list/mapping"
            )
            self.assertIsNotNone(mapping)
            assert mapping is not None
            self.assertEqual(
                mapping.get("local-root"),
                os.path.realpath(odoo_src),
            )

    def test_update_pycharm_run_configuration_writes_dap_attach_run_xml(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)
            env = make_debugger_env_mock(
                project_dir=project_dir,
                mapped_folders=[
                    MappedPath(local=odoo_src, docker="/home/odoo/odoo"),
                ],
            )
            configurator = PycharmConfigurator(env)
            configurator.update_pycharm_run_configuration()
            path = configurator.run_config_path()
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as run_file:
                content = run_file.read()
            self.assertIn("PythonDapAttachConfiguration", content)

    def test_update_pycharm_run_configuration_writes_debug_server_run_xml(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)
            env = make_debugger_env_mock(
                project_dir=project_dir,
                mapped_folders=[
                    MappedPath(local=odoo_src, docker="/home/odoo/odoo"),
                ],
            )
            env.user_env.debugger_backend = DEBUGGER_BACKEND_PYDEVD_CONNECT
            configurator = PycharmConfigurator(env)
            configurator.update_pycharm_run_configuration()
            path = configurator.run_config_path()
            self.assertTrue(path.endswith(f"{PYCHARM_DEBUG_SERVER_RUN_CONFIG_BASENAME}.run.xml"))
            with open(path, encoding="utf-8") as run_file:
                content = run_file.read()
            self.assertIn("PyRemoteDebugConfigurationType", content)
            self.assertIn("Python Debug Server", content)

    def test_should_generate_true_for_pydevd_connect(self) -> None:
        env = make_debugger_env_mock(
            project_dir="/proj",
            mapped_folders=[],
        )
        env.user_env.debugger_backend = DEBUGGER_BACKEND_PYDEVD_CONNECT
        configurator = PycharmConfigurator(env)
        profile = configurator.build_debugger_profile()
        self.assertTrue(configurator.should_generate(profile))

    def test_should_generate_false_for_unknown_backend(self) -> None:
        env = make_debugger_env_mock(
            project_dir="/proj",
            mapped_folders=[],
        )
        configurator = PycharmConfigurator(env)
        profile = MagicMock()
        profile.debugger.backend = "unknown"
        self.assertFalse(configurator.should_generate(profile))


if __name__ == "__main__":
    unittest.main()
