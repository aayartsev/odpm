import importlib
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from dev_project.check_system import SystemChecker
from dev_project.errors import OdpmError, SystemCheckError
from dev_project.inside_docker_app import parse_args as parse_args_module
from dev_project.odpm_pipeline import OdpmPipeline


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


class SystemCheckerDockerTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.check_system = False
        config.user_env.backups = "/tmp/backups"
        config.user_env.odoo_projects_dir = "/tmp/odoo-projects"
        return config

    @patch.object(SystemChecker, "check_file_system")
    @patch("dev_project.check_system.platform.system", return_value="Darwin")
    @patch("dev_project.check_system.run_checked")
    def test_check_docker_raises_system_check_error_when_docker_unavailable(
        self, mock_checked, _mock_platform, _mock_fs
    ):
        checker = SystemChecker(self._config())
        mock_checked.return_value = MagicMock(returncode=0, stdout="broken", stderr="")
        with self.assertRaises(SystemCheckError):
            checker.check_docker()

    @patch.object(SystemChecker, "check_file_system")
    @patch("dev_project.check_system.platform.system", return_value="Darwin")
    @patch("dev_project.check_system.run_checked")
    def test_check_docker_calls_ensure_base_image_when_docker_ok(
        self, mock_checked, _mock_platform, _mock_fs
    ):
        config = self._config()
        config.project_env = MagicMock()
        checker = SystemChecker(config)
        mock_checked.return_value = MagicMock(
            returncode=0,
            stdout="Server:\n Version 24.0",
            stderr="",
        )
        checker.check_docker()
        config.project_env.ensure_base_image.assert_called_once()


class OdpmPipelineErrorHandlingTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.sys.exit")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    def test_run_exits_on_system_check_error(
        self, mock_prepare, _mock_setup, mock_exit
    ):
        mock_prepare.side_effect = SystemCheckError("docker down", exit_code=1)
        pipeline = OdpmPipeline(Namespace(), "/opt/odpm")
        pipeline.run()
        mock_exit.assert_called_once_with(1)

    def test_run_catches_system_check_error_as_odpm_error(self):
        self.assertTrue(issubclass(SystemCheckError, OdpmError))


if __name__ == "__main__":
    unittest.main()
