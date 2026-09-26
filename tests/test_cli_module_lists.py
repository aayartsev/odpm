"""Tests for CLI -i/-u module list resolution."""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.compose.service_builder import ComposeServiceBuilder
from dev_project.container_config.config import ContainerConfig
from dev_project.errors import ConfigError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.config.transforms.modules import (
    modules_csv_for_odoo_flag,
    modules_csv_for_update_list,
    normalize_cli_module_csv,
)
from dev_project.scenario_policy import ScenarioPolicy


class NormalizeCliModuleCsvTests(unittest.TestCase):
    def test_happy_path_strips_and_joins(self):
        self.assertEqual(normalize_cli_module_csv(" sale , crm "), "sale,crm")

    def test_rejects_empty_lists(self):
        for raw in ("", "  ", ",", " , , "):
            with self.subTest(raw=raw):
                with self.assertRaises(ConfigError):
                    normalize_cli_module_csv(raw)


class ModulesCsvResolveTests(unittest.TestCase):
    def test_odoo_flag_absent_omits(self):
        self.assertIsNone(modules_csv_for_odoo_flag(None, "sale"))
        self.assertIsNone(modules_csv_for_odoo_flag(False, "sale"))

    def test_odoo_flag_bare_uses_settings(self):
        self.assertEqual(modules_csv_for_odoo_flag(True, "sale,crm"), "sale,crm")
        self.assertIsNone(modules_csv_for_odoo_flag(True, ""))

    def test_odoo_flag_cli_overrides(self):
        self.assertEqual(
            modules_csv_for_odoo_flag("other", "sale"),
            "other",
        )

    def test_update_list_keeps_settings_without_cli_csv(self):
        self.assertEqual(modules_csv_for_update_list(None, "sale"), "sale")
        self.assertEqual(modules_csv_for_update_list(True, "sale"), "sale")
        self.assertEqual(modules_csv_for_update_list(None, ""), "")

    def test_update_list_cli_overrides(self):
        self.assertEqual(modules_csv_for_update_list("cli_mod", "sale"), "cli_mod")


class ComposeServiceBuilderModuleArgvTests(unittest.TestCase):
    def _make_config(self):
        config = MagicMock()
        config.project_dir = "/tmp/odpm-test-project"
        config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.container_run_mode = constants.RUN_MODE_ODOO
        config.arguments = OdpmCliArgs()
        config.dev_mode = False
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.docker_project_dir = "/home/odoo"
        config.docker_inside_app = "/home/odoo/dev_project/inside_docker_app"
        config.docker_venv_dir = "/home/odoo/.venv"
        config.platform_name = "odoo"
        config.odoo_version = "19.0"
        config.init_modules = "from_settings"
        config.update_modules = "upd_settings"
        config.docker_odoo_project_dir_path = "/home/odoo/extra-addons/project"
        config.docker_temp_tests_dir = "/home/odoo/odoo_tests"
        config.requirements_txt = []
        config.generate_odoo_conf_docker_data = MagicMock()
        return config

    @patch("dev_project.compose.service_builder.persist_runtime_config")
    def test_bare_i_uses_settings(self, _mock_persist):
        config = self._make_config()
        config.arguments = replace(config.arguments, i=True)
        ComposeServiceBuilder(config).build()
        command = config.compose_service.command
        self.assertIn("-i", command)
        self.assertIn("from_settings", command)

    @patch("dev_project.compose.service_builder.persist_runtime_config")
    def test_cli_i_overrides_settings(self, _mock_persist):
        config = self._make_config()
        config.arguments = replace(config.arguments, i="other")
        ComposeServiceBuilder(config).build()
        command = config.compose_service.command
        self.assertIn("-i", command)
        self.assertIn("other", command)
        self.assertNotIn("from_settings", command)

    @patch("dev_project.compose.service_builder.persist_runtime_config")
    def test_absent_i_omits_flag(self, _mock_persist):
        config = self._make_config()
        ComposeServiceBuilder(config).build()
        command = config.compose_service.command
        self.assertNotIn("-i", command)
        self.assertNotIn("-u", command)


class ContainerConfigModulesToUpdateTests(unittest.TestCase):
    def _host_config(self, *, update_modules: str, u):
        config = MagicMock()
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.odoo_config_data = {}
        config.docker_path_odoo_conf = "/home/odoo/odoo.conf"
        config.arguments = OdpmCliArgs(u=u)
        config.db_creation_data = constants.DEFAULT_DB_CREATION_DATA
        config.db_manager_password = ""
        config.docker_venv_dir = "/home/odoo/.venv"
        config.docker_project_dir = "/home/odoo"
        config.requirements_txt = []
        config.odoo_version = "19.0"
        config.python_version = "3.12"
        config.platform_name = "odoo"
        config.arch = "amd64"
        config.sql_queries = []
        config.update_modules = update_modules
        config.docker_dirs_with_addons = []
        config.container_run_mode = constants.RUN_MODE_ODOO
        config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        policy = MagicMock()
        policy.venv_mode = constants.VENV_MODE_FRESH
        policy.mount_runtime_config_from_host.return_value = False
        policy.install_debugpy = False
        config.policy = policy
        return config

    @patch(
        "dev_project.config.payload.compute_venv_lock_hash",
        return_value="lock-hash",
    )
    def test_no_u_uses_settings(self, _mock_hash):
        config = self._host_config(update_modules="sale,purchase", u=None)
        container = ContainerConfig.from_odpm_config(config)
        self.assertEqual(container.modules_to_update, ["sale", "purchase"])

    @patch(
        "dev_project.config.payload.compute_venv_lock_hash",
        return_value="lock-hash",
    )
    def test_u_csv_overrides_settings(self, _mock_hash):
        config = self._host_config(update_modules="sale", u="cli_mod")
        container = ContainerConfig.from_odpm_config(config)
        self.assertEqual(container.modules_to_update, ["cli_mod"])


if __name__ == "__main__":
    unittest.main()
