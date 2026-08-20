"""Tests for scenario-first CI env wizard (ADR-018)."""

from __future__ import annotations

import importlib
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.debugger.constants import DEFAULT_DEBUGGER_BACKEND


class UserEnvCiWizardTests(unittest.TestCase):
    def test_ci_wizard_prompts_projects_and_builder_not_ports(self) -> None:
        wizard_module = importlib.import_module("dev_project.host.user_env_wizard")
        user_env_module = importlib.import_module("dev_project.host.user_env")
        # scenario=ci(3), locale, projects, builder=docker(1), push=no
        mock_prompt = MagicMock(side_effect=["3", "", "", "1", ""])
        with patch.object(wizard_module, "_prompt_input", mock_prompt):
            user_env = user_env_module.CreateUserEnvironment.__new__(
                user_env_module.CreateUserEnvironment
            )
            env_data = user_env._build_env_data_interactive()
        self.assertEqual(env_data["ODPM_SCENARIO"], constants.CI_SCENARIO)
        self.assertEqual(
            env_data[constants.ODPM_CI_IMAGE_BUILDER_ENV],
            constants.CI_IMAGE_BUILDER_DOCKER,
        )
        self.assertEqual(env_data[constants.ODPM_CI_IMAGE_PUSH_ENV], "0")
        self.assertNotIn(constants.ODPM_KANIKO_EXECUTOR_MODE_ENV, env_data)
        self.assertEqual(mock_prompt.call_count, 5)

    def test_ci_kaniko_asks_mode_registry_default_direct(self) -> None:
        wizard_module = importlib.import_module("dev_project.host.user_env_wizard")
        user_env_module = importlib.import_module("dev_project.host.user_env")
        # scenario=ci, locale, projects, builder=kaniko(2), push, mode=Enter(direct), registry
        mock_prompt = MagicMock(
            side_effect=["3", "", "", "2", "", "", "registry.example.com/odpm"]
        )
        with patch.object(wizard_module, "_prompt_input", mock_prompt):
            user_env = user_env_module.CreateUserEnvironment.__new__(
                user_env_module.CreateUserEnvironment
            )
            env_data = user_env._build_env_data_interactive()
        self.assertEqual(
            env_data[constants.ODPM_CI_IMAGE_BUILDER_ENV],
            constants.CI_IMAGE_BUILDER_KANIKO,
        )
        self.assertEqual(
            env_data[constants.ODPM_KANIKO_EXECUTOR_MODE_ENV],
            constants.KANIKO_EXECUTOR_MODE_DIRECT,
        )
        self.assertEqual(
            env_data[constants.ODPM_BASE_IMAGE_REGISTRY_ENV],
            "registry.example.com/odpm",
        )

    def test_developer_still_prompts_ports_and_debugger(self) -> None:
        wizard_module = importlib.import_module("dev_project.host.user_env_wizard")
        user_env_module = importlib.import_module("dev_project.host.user_env")
        # scenario, locale, backup, projects, 4 ports, backend, ide
        mock_prompt = MagicMock(
            side_effect=["1", "", "", "", "", "", "", "", "", ""]
        )
        with patch.object(wizard_module, "_prompt_input", mock_prompt):
            user_env = user_env_module.CreateUserEnvironment.__new__(
                user_env_module.CreateUserEnvironment
            )
            env_data = user_env._build_env_data_interactive()
        self.assertEqual(env_data["ODPM_SCENARIO"], constants.DEVELOPER_SCENARIO)
        self.assertEqual(
            env_data["ODPM_DEBUGGER_BACKEND"], DEFAULT_DEBUGGER_BACKEND
        )
        self.assertEqual(mock_prompt.call_count, 10)

    def test_server_skips_debugger_and_gevent_prompts(self) -> None:
        wizard_module = importlib.import_module("dev_project.host.user_env_wizard")
        user_env_module = importlib.import_module("dev_project.host.user_env")
        # scenario=server(2), locale, backup, projects, odoo, postgres
        mock_prompt = MagicMock(side_effect=["2", "", "", "", "", ""])
        with patch.object(wizard_module, "_prompt_input", mock_prompt):
            user_env = user_env_module.CreateUserEnvironment.__new__(
                user_env_module.CreateUserEnvironment
            )
            env_data = user_env._build_env_data_interactive()
        self.assertEqual(env_data["ODPM_SCENARIO"], constants.SERVER_SCENARIO)
        self.assertEqual(env_data["GEVENT_PORT"], constants.GEVENT_DEFAULT_PORT)
        self.assertEqual(mock_prompt.call_count, 6)


if __name__ == "__main__":
    unittest.main()
