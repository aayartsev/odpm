import importlib
import os
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.host_cli.args import OdpmCliArgs
from tests.cli_test_helpers import cli_args
from dev_project.check_system import SystemChecker
from dev_project.errors import (
    ConfigError,
    GitError,
    OdpmError,
    ProjectDirError,
    SubprocessError,
    SystemCheckError,
)
from dev_project.inside_docker_app import parse_args as parse_args_module
from dev_project.odpm_pipeline import OdpmPipeline
from dev_project.project_dir_manager import ProjectDirManager


class ParseArgsLazyTests(unittest.TestCase):
    def test_module_has_no_pre_parsed_args(self):
        self.assertTrue(callable(parse_args_module.parse_args))
        self.assertFalse(hasattr(parse_args_module, "args"))

    def test_import_parse_args_module_does_not_parse_argv(self):
        with patch.object(parse_args_module.arg_parser, "parse_args") as mock_parse:
            importlib.reload(parse_args_module)
        mock_parse.assert_not_called()

    def test_parse_args_delegates_to_arg_parser(self):
        with patch.object(
            parse_args_module.arg_parser,
            "parse_args",
            return_value=Namespace(),
        ) as mock_parse:
            result = parse_args_module.parse_args(["--skip-start"])
        mock_parse.assert_called_once_with(["--skip-start"])
        self.assertIsInstance(result, Namespace)

    def test_parse_args_plan_subcommand_parses_natively(self):
        with patch.object(
            parse_args_module.arg_parser,
            "parse_args",
            return_value=Namespace(command="plan"),
        ) as mock_parse:
            parse_args_module.parse_args(["plan", "--skip-start"])
        mock_parse.assert_called_once_with(["plan", "--skip-start"])


class SystemCheckerDockerTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.check_system = False
        config.user_env.backups = "/tmp/backups"
        config.user_env.odoo_projects_dir = "/tmp/odoo-projects"
        return config

    def _checker(self, config: MagicMock | None = None) -> SystemChecker:
        return SystemChecker(config or self._config(), MagicMock())

    @patch.object(SystemChecker, "check_file_system")
    @patch("dev_project.check_system.platform.system", return_value="Darwin")
    @patch("dev_project.check_system.run_or_raise")
    def test_check_docker_raises_system_check_error_when_docker_unavailable(
        self, mock_run_or_raise, _mock_platform, _mock_fs
    ):
        checker = self._checker()
        mock_run_or_raise.return_value = MagicMock(
            returncode=0, stdout="broken", stderr=""
        )
        with self.assertRaises(SystemCheckError):
            checker.check_docker()

    @patch.object(SystemChecker, "check_file_system")
    @patch("dev_project.check_system.platform.system", return_value="Darwin")
    @patch("dev_project.check_system.run_or_raise")
    def test_check_docker_calls_ensure_base_image_when_docker_ok(
        self, mock_run_or_raise, _mock_platform, _mock_fs
    ):
        config = self._config()
        project_environment = MagicMock()
        checker = SystemChecker(config, project_environment)
        mock_run_or_raise.return_value = MagicMock(
            returncode=0,
            stdout="Server:\n Version 24.0",
            stderr="",
        )
        checker.check_docker()
        project_environment.ensure_base_image.assert_called_once()


class SystemCheckerExtraTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.check_system = False
        config.user_env.backups = "/tmp/backups"
        config.user_env.odoo_projects_dir = "/tmp/odoo-projects"
        config.user_env.odoo_port = 8069
        config.user_env.debugger_port = 5678
        config.user_env.postgres_port = 5432
        config.user_env.gevent_port = 8072
        return config

    def _checker(self, config: MagicMock | None = None) -> SystemChecker:
        return SystemChecker(config or self._config(), MagicMock())

    @patch("dev_project.check_system.run_logged")
    @patch("dev_project.check_system.run_or_raise")
    def test_check_running_containers_stops_postgres_conflict_when_check_system_disabled(
        self, mock_run_or_raise, mock_logged
    ):
        container_json = (
            '{"ID":"abc123","Ports":"0.0.0.0:5432->5432/tcp, '
            '0.0.0.0:8069->8069/tcp"}'
        )
        mock_run_or_raise.return_value = MagicMock(
            returncode=0,
            stdout=f"'{container_json}'",
            stderr="",
        )
        checker = self._checker()
        checker.check_running_containers()
        mock_logged.assert_called_once_with(["docker", "stop", "abc123"])

    @patch("dev_project.check_system.run_logged")
    @patch("dev_project.check_system.run_or_raise")
    def test_check_running_containers_stops_gevent_port_conflict(
        self, mock_run_or_raise, mock_logged
    ):
        container_json = '{"ID":"geo456","Ports":"0.0.0.0:8072->8072/tcp"}'
        mock_run_or_raise.return_value = MagicMock(
            returncode=0,
            stdout=f"'{container_json}'",
            stderr="",
        )
        checker = self._checker()
        checker.check_running_containers()
        mock_logged.assert_called_once_with(["docker", "stop", "geo456"])

    @patch("dev_project.check_system.run_or_raise")
    def test_check_running_containers_raises_when_docker_list_fails(
        self, mock_run_or_raise
    ):
        from dev_project.errors import SubprocessError

        mock_run_or_raise.side_effect = SubprocessError(
            "docker down",
            argv=["docker", "container", "ls"],
            returncode=1,
            stderr="denied",
        )
        checker = self._checker()
        with self.assertRaises(SystemCheckError) as ctx:
            checker.check_running_containers()
        self.assertIn("docker down", str(ctx.exception))

    @patch.object(SystemChecker, "check_file_system")
    @patch("dev_project.check_system.run_or_raise")
    def test_check_git_raises_system_check_error_when_git_missing(
        self, mock_run_or_raise, _mock_fs
    ):
        mock_run_or_raise.return_value = MagicMock(returncode=0, stdout="broken", stderr="")
        checker = self._checker()
        with self.assertRaises(SystemCheckError):
            checker.check_git()

    @patch("dev_project.check_system.run_checked")
    def test_check_docker_compose_raises_system_check_error(self, mock_checked):
        config = self._config()
        config.no_log_prefix = True
        config.docker_compose_command = constants.DEFAULT_DOCKER_COMPOSE_COMMAND
        checker = self._checker(config)
        mock_checked.return_value = MagicMock(returncode=0, stdout="unknown tool", stderr="")
        with self.assertRaises(SystemCheckError):
            checker.check_docker_compose()

    @patch("dev_project.check_system.os.makedirs", side_effect=OSError("denied"))
    @patch("dev_project.check_system.os.path.exists", return_value=False)
    def test_check_file_system_raises_system_check_error(self, _mock_exists, _mock_mkdir):
        checker = SystemChecker.__new__(SystemChecker)
        checker.config = self._config()
        with self.assertRaises(SystemCheckError):
            checker.check_file_system()


class ProjectDirManagerErrorTests(unittest.TestCase):
    def test_not_project_directory_raises_project_dir_error_exit_zero(self):
        with tempfile.TemporaryDirectory() as project_dir:
            args = cli_args(odoo_git_link=None)
            with self.assertRaises(ProjectDirError) as ctx:
                ProjectDirManager(project_dir, args, "/opt/odpm")
            self.assertEqual(ctx.exception.exit_code, 0)

    def test_odoo_git_link_without_init_raises_project_dir_error(self):
        with tempfile.TemporaryDirectory() as project_dir:
            service_dir = os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY)
            os.makedirs(service_dir)
            args = cli_args(odoo_git_link="git@github.com:org/odoo.git")
            with self.assertRaises(ProjectDirError) as ctx:
                ProjectDirManager(project_dir, args, "/opt/odpm")
            self.assertEqual(ctx.exception.exit_code, 1)


class OdpmPipelineErrorHandlingTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.sys.exit")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    def test_run_exits_on_system_check_error(
        self, mock_prepare, _mock_setup, mock_exit
    ):
        mock_prepare.side_effect = SystemCheckError("docker down", exit_code=1)
        pipeline = OdpmPipeline(OdpmCliArgs(), "/opt/odpm")
        pipeline.run()
        mock_exit.assert_called_once_with(1)

    def test_run_catches_system_check_error_as_odpm_error(self):
        self.assertTrue(issubclass(SystemCheckError, OdpmError))

    @patch("dev_project.odpm_pipeline.sys.exit")
    def test_run_exits_zero_on_version(self, mock_exit):
        pipeline = OdpmPipeline(OdpmCliArgs(version=True), "/opt/odpm")
        pipeline.run()
        mock_exit.assert_called_once_with(0)

    @patch("dev_project.odpm_pipeline.sys.exit")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_exits_zero_on_config_error_exit_code_zero(self, mock_setup, mock_exit):
        mock_setup.side_effect = ConfigError("", exit_code=0)
        pipeline = OdpmPipeline(OdpmCliArgs(), "/opt/odpm")
        pipeline.run()
        mock_exit.assert_called_once_with(0)

    def test_git_error_and_project_dir_error_are_odpm_errors(self):
        self.assertIsInstance(GitError("git"), OdpmError)
        self.assertIsInstance(ProjectDirError("dir", exit_code=0), OdpmError)

    def test_subprocess_error_is_odpm_error(self):
        self.assertIsInstance(
            SubprocessError("failed", argv=["docker"], returncode=1),
            OdpmError,
        )


if __name__ == "__main__":
    unittest.main()
