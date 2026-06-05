import unittest
from unittest.mock import MagicMock, patch

from dev_project.errors import (
    ConfigError,
    GitError,
    OdpmError,
    PipelineError,
    ProjectDirError,
    SystemCheckError,
)
from dev_project.subprocess_runner import CommandResult, run_checked, run_logged


class OdpmErrorHierarchyTests(unittest.TestCase):
    def test_pipeline_error_is_odpm_error(self):
        error = PipelineError("failed", exit_code=2)
        self.assertIsInstance(error, OdpmError)
        self.assertEqual(error.exit_code, 2)

    def test_system_check_error_is_odpm_error(self):
        self.assertIsInstance(SystemCheckError("docker"), OdpmError)

    def test_config_error_is_odpm_error(self):
        self.assertIsInstance(ConfigError("config"), OdpmError)

    def test_git_error_is_odpm_error(self):
        self.assertIsInstance(GitError("git"), OdpmError)

    def test_project_dir_error_supports_exit_code_zero(self):
        error = ProjectDirError("", exit_code=0)
        self.assertEqual(error.exit_code, 0)


class SubprocessRunnerTests(unittest.TestCase):
    @patch("dev_project.subprocess_runner.subprocess.run")
    def test_run_checked_captures_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )
        result = run_checked(["echo", "ok"], cwd="/tmp")
        self.assertEqual(result, CommandResult(0, "ok", ""))
        mock_run.assert_called_once_with(
            ["echo", "ok"],
            cwd="/tmp",
            capture_output=True,
            text=True,
        )

    @patch("dev_project.subprocess_runner.subprocess.run")
    def test_run_logged_returns_exit_code(self, mock_run):
        mock_run.return_value = MagicMock(returncode=5)
        self.assertEqual(run_logged(["docker", "compose", "up"], cwd="/proj"), 5)
        mock_run.assert_called_once_with(
            ["docker", "compose", "up"],
            cwd="/proj",
        )


if __name__ == "__main__":
    unittest.main()
