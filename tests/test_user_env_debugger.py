"""Tests for debugger-related .env parsing and interactive prompts."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from dev_project import constants
from dev_project.debugger.constants import (
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
    DEFAULT_DEBUGGER_BACKEND,
    DEFAULT_DEBUGGER_CONNECT_HOST,
    DEFAULT_ODPM_IDE,
    ODPM_DEBUGGER_BACKEND_ENV,
    ODPM_DEBUGGER_CONNECT_HOST_ENV,
    ODPM_DEBUGGER_SUSPEND_ENV,
    ODPM_IDE_ENV,
)
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.user_env import CreateUserEnvironment
from dev_project.project_dir_manager import ProjectDirManager


def _program_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class UserEnvDebuggerTests(unittest.TestCase):
    def _pd_manager(self, project_dir: str) -> ProjectDirManager:
        os.makedirs(
            os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
            exist_ok=True,
        )
        return ProjectDirManager(project_dir, OdpmCliArgs(), _program_dir())

    def _write_minimal_env(self, project_dir: str) -> None:
        env_path = os.path.join(project_dir, ".env")
        with open(env_path, "w", encoding="utf-8") as env_file:
            env_file.write(
                "\n".join(
                    [
                        "BACKUP_DIR=/tmp/backups",
                        "ODOO_PROJECTS_DIR=/tmp/projects",
                        "PATH_TO_SSH_KEY=",
                        "ODOO_PORT=8069",
                        "POSTGRES_PORT=5432",
                        "DEBUGGER_PORT=5678",
                        "GEVENT_PORT=8072",
                        "ODPM_SCENARIO=developer",
                    ]
                )
            )

    def test_parse_env_file_applies_debugger_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            self._write_minimal_env(project_dir)
            user_env = CreateUserEnvironment(self._pd_manager(project_dir))
            self.assertEqual(user_env.debugger_backend, DEFAULT_DEBUGGER_BACKEND)
            self.assertEqual(user_env.odpm_ide, DEFAULT_ODPM_IDE)

    @patch("dev_project.host.user_env.prompt_input")
    def test_interactive_env_includes_debugger_keys(self, mock_prompt) -> None:
        mock_prompt.side_effect = ["", "", "", "", "", "", "1", "", "", ""]

        with tempfile.TemporaryDirectory() as project_dir:
            self._write_minimal_env(project_dir)
            user_env = CreateUserEnvironment(self._pd_manager(project_dir))
            env_data = user_env._build_env_data_interactive()
            self.assertEqual(
                env_data[ODPM_DEBUGGER_BACKEND_ENV],
                DEFAULT_DEBUGGER_BACKEND,
            )
            self.assertEqual(env_data[ODPM_IDE_ENV], DEFAULT_ODPM_IDE)

    @patch("dev_project.host.user_env.prompt_input")
    def test_interactive_pydevd_connect_prompts_connect_host_and_suspend(
        self, mock_prompt
    ) -> None:
        mock_prompt.side_effect = [
            "",
            "",
            "",
            "",
            "",
            "",
            "1",
            "2",
            "",
            "",
            "y",
            "",
        ]

        with tempfile.TemporaryDirectory() as project_dir:
            self._write_minimal_env(project_dir)
            user_env = CreateUserEnvironment(self._pd_manager(project_dir))
            env_data = user_env._build_env_data_interactive()
            self.assertEqual(
                env_data[ODPM_DEBUGGER_BACKEND_ENV],
                DEBUGGER_BACKEND_PYDEVD_CONNECT,
            )
            self.assertEqual(
                env_data[ODPM_DEBUGGER_CONNECT_HOST_ENV],
                DEFAULT_DEBUGGER_CONNECT_HOST,
            )
            self.assertEqual(env_data[ODPM_DEBUGGER_SUSPEND_ENV], "1")


if __name__ == "__main__":
    unittest.main()
