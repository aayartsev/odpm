"""Tests for PyCharm Attach to DAP run configuration generation."""

from __future__ import annotations

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.project_env.services.pycharm_configurator import PycharmConfigurator
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
            xml_text = configurator.build_run_config_xml(profile)

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

    def test_update_pycharm_run_configuration_writes_run_xml(self) -> None:
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

    def test_should_generate_false_for_unknown_backend(self) -> None:
        env = make_debugger_env_mock(
            project_dir="/proj",
            mapped_folders=[],
        )
        env.user_env.debugger_backend = "pydevd_connect"
        configurator = PycharmConfigurator(env)
        profile = MagicMock()
        profile.debugger.backend = "pydevd_connect"
        self.assertFalse(configurator.should_generate(profile))


if __name__ == "__main__":
    unittest.main()
