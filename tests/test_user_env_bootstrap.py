"""Tests for .env path resolution and default file bootstrap."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.host.user_env import CreateUserEnvironment
from dev_project.project_dir_manager import ProjectDirManager
from tests.cli_test_helpers import cli_args


def _program_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _make_pd_manager(project_dir: str, *, home_dir: str) -> ProjectDirManager:
    os.makedirs(
        os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
        exist_ok=True,
    )
    with patch.dict(os.environ, {"HOME": home_dir}, clear=False):
        return ProjectDirManager(project_dir, cli_args(odoo_git_link=None), _program_dir())


def _write_minimal_env_file(
    path: str,
    *,
    extra_lines: list[str] | None = None,
) -> None:
    lines = [
        "BACKUP_DIR=/tmp/backups",
        "ODOO_PROJECTS_DIR=/tmp/projects",
        "PATH_TO_SSH_KEY=",
        "ODOO_PORT=8069",
        "POSTGRES_PORT=5432",
        "DEBUGGER_PORT=5678",
        "GEVENT_PORT=8072",
        f"ODPM_SCENARIO={constants.DEVELOPER_SCENARIO}",
    ]
    if extra_lines:
        lines.extend(extra_lines)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


class UserEnvBootstrapTests(unittest.TestCase):
    def test_resolve_env_file_path_prefers_project_local(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = os.path.join(project_dir, constants.ENV_FILE_NAME)
            Path(project_env).write_text("BACKUP_DIR=/x\n", encoding="utf-8")
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            user_env = CreateUserEnvironment.__new__(CreateUserEnvironment)
            user_env.pd_manager = pd_manager
            user_env.config_home_dir = pd_manager.home_config_dir

            self.assertEqual(user_env.resolve_env_file_path(), project_env)

    def test_resolve_env_file_path_falls_back_to_home(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            user_env = CreateUserEnvironment.__new__(CreateUserEnvironment)
            user_env.pd_manager = pd_manager
            user_env.config_home_dir = pd_manager.home_config_dir
            expected = os.path.join(pd_manager.home_config_dir, constants.ENV_FILE_NAME)

            self.assertEqual(user_env.resolve_env_file_path(), expected)

    @patch("dev_project.interactive.stdin_is_interactive", return_value=False)
    def test_ensure_default_env_file_skips_when_present(self, _mock_tty):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, constants.ENV_FILE_NAME)
            Path(env_path).write_text("BACKUP_DIR=/keep\n", encoding="utf-8")
            user_env = CreateUserEnvironment.__new__(CreateUserEnvironment)
            user_env.create_env_file_noninteractive = MagicMock()

            user_env.ensure_default_env_file(env_path)

            user_env.create_env_file_noninteractive.assert_not_called()
            self.assertEqual(Path(env_path).read_text(encoding="utf-8"), "BACKUP_DIR=/keep\n")

    @patch("dev_project.interactive.stdin_is_interactive", return_value=False)
    def test_ensure_default_env_file_raises_without_configuration(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            user_env = CreateUserEnvironment.__new__(CreateUserEnvironment)
            user_env.pd_manager = pd_manager
            env_path = os.path.join(
                home_dir, constants.CONFIG_DIR_IN_HOME_DIR, constants.ENV_FILE_NAME
            )

            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                with self.assertRaises(ConfigError):
                    user_env.ensure_default_env_file(env_path)

    @patch("dev_project.interactive.stdin_is_interactive", return_value=False)
    def test_ensure_default_env_file_creates_from_environment(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            user_env = CreateUserEnvironment.__new__(CreateUserEnvironment)
            user_env.pd_manager = pd_manager
            env_path = os.path.join(
                home_dir, constants.CONFIG_DIR_IN_HOME_DIR, constants.ENV_FILE_NAME
            )
            env = {
                "HOME": home_dir,
                "BACKUP_DIR": "/tmp/ci-backups",
                "ODOO_PROJECTS_DIR": "/tmp/ci-projects",
            }
            with patch.dict(os.environ, env, clear=True):
                user_env.ensure_default_env_file(env_path)

            self.assertTrue(os.path.isfile(env_path))
            content = Path(env_path).read_text(encoding="utf-8")
            self.assertIn("BACKUP_DIR=/tmp/ci-backups", content)
            self.assertIn("ODOO_PROJECTS_DIR=/tmp/ci-projects", content)

    def test_project_dotenv_dict_includes_custom_keys_with_original_case(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = os.path.join(project_dir, constants.ENV_FILE_NAME)
            _write_minimal_env_file(
                project_env,
                extra_lines=[
                    "ODOO_PLATFORM_DIR=/home/dev/odoo/19.0",
                    "GIT_HOST=git.company.example",
                ],
            )
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            with patch.dict(os.environ, {"HOME": home_dir}, clear=False):
                user_env = CreateUserEnvironment(pd_manager)

            dotenv = user_env.project_dotenv_dict()

            self.assertEqual(dotenv["ODOO_PLATFORM_DIR"], "/home/dev/odoo/19.0")
            self.assertEqual(dotenv["GIT_HOST"], "git.company.example")
            self.assertEqual(dotenv["BACKUP_DIR"], "/tmp/backups")

    def test_project_dotenv_dict_returns_copy(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = os.path.join(project_dir, constants.ENV_FILE_NAME)
            _write_minimal_env_file(project_env)
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            with patch.dict(os.environ, {"HOME": home_dir}, clear=False):
                user_env = CreateUserEnvironment(pd_manager)

            dotenv = user_env.project_dotenv_dict()
            dotenv["BACKUP_DIR"] = "/mutated"

            self.assertEqual(user_env.project_dotenv_dict()["BACKUP_DIR"], "/tmp/backups")


if __name__ == "__main__":
    unittest.main()
