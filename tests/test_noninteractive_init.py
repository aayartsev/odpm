import os
import tempfile
import unittest
from dev_project.host_cli.args import OdpmCliArgs
from tests.cli_test_helpers import cli_args
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config.loader import ConfigLoader
from dev_project.errors import ConfigError
from dev_project.host_user_env import CreateUserEnvironment
from dev_project.project_dir_manager import ProjectDirManager


def _program_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _make_pd_manager(project_dir: str, *, home_dir: str) -> ProjectDirManager:
    os.makedirs(
        os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
        exist_ok=True,
    )
    args = cli_args(odoo_git_link=None)
    with patch.dict(os.environ, {"HOME": home_dir}, clear=False):
        return ProjectDirManager(project_dir, args, _program_dir())


class NonInteractiveOdpmJsonTests(unittest.TestCase):
    @patch("dev_project.config.loader.stdin_is_interactive", return_value=False)
    def test_create_default_odpm_json_raises_without_odoo_version(self, _mock_tty):
        config = MagicMock()
        config.config_json_content = {}
        config.arguments = OdpmCliArgs(odoo_version=None)
        config._raw_odpm_json = {}

        with self.assertRaises(ConfigError):
            ConfigLoader(config).create_default_odpm_json_content()

    @patch("dev_project.config.loader.stdin_is_interactive", return_value=False)
    def test_create_default_odpm_json_uses_cli_odoo_version(self, _mock_tty):
        config = MagicMock()
        config.config_json_content = {}
        config.arguments = OdpmCliArgs(
            odoo_version="18.0",
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
            odoo_git_link=None,
            platform_name=None,
        )
        config._raw_odpm_json = {"odpm_version": constants.ODPM_VERSION}

        content = ConfigLoader(config).create_default_odpm_json_content()

        self.assertEqual(content["odoo_version"], "18.0")


class NonInteractiveEnvFileTests(unittest.TestCase):
    @patch("dev_project.host_user_env.stdin_is_interactive", return_value=False)
    def test_missing_env_raises_without_configuration(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                with self.assertRaises(ConfigError):
                    CreateUserEnvironment(pd_manager)

    @patch("dev_project.host_user_env.stdin_is_interactive", return_value=False)
    def test_missing_env_creates_from_environment_variables(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            env = {
                "HOME": home_dir,
                "BACKUP_DIR": "/tmp/backups",
                "ODOO_PROJECTS_DIR": "/tmp/projects",
                "ODPM_SCENARIO": constants.CI_SCENARIO,
            }
            with patch.dict(os.environ, env, clear=True):
                user_env = CreateUserEnvironment(pd_manager)

            env_file = Path(home_dir) / constants.CONFIG_DIR_IN_HOME_DIR / constants.ENV_FILE_NAME
            self.assertTrue(env_file.is_file())
            self.assertEqual(user_env.backups, "/tmp/backups")
            self.assertEqual(user_env.odoo_projects_dir, "/tmp/projects")
            self.assertEqual(user_env.odpm_scenario, constants.CI_SCENARIO)

    @patch("dev_project.host_user_env.stdin_is_interactive", return_value=False)
    def test_project_env_file_used_without_prompt(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = os.path.join(project_dir, constants.ENV_FILE_NAME)
            with open(project_env, "w", encoding="utf-8") as writer:
                writer.write(
                    "BACKUP_DIR=/project/backups\n"
                    "ODOO_PROJECTS_DIR=/project/repos\n"
                    "PATH_TO_SSH_KEY=\n"
                    "ODOO_PORT=8069\n"
                    "POSTGRES_PORT=5432\n"
                    "DEBUGGER_PORT=5678\n"
                    "GEVENT_PORT=8072\n"
                    f"ODPM_SCENARIO={constants.DEVELOPER_SCENARIO}\n"
                )

            os.makedirs(
                os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
                exist_ok=True,
            )
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                pd_manager = ProjectDirManager(
                    project_dir,
                    cli_args(odoo_git_link=None),
                    _program_dir(),
                )
                user_env = CreateUserEnvironment(pd_manager)

            self.assertEqual(user_env.env_file, project_env)
            self.assertEqual(user_env.backups, "/project/backups")


if __name__ == "__main__":
    unittest.main()
