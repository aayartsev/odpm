import unittest
from unittest.mock import patch

from dev_project.inside_docker_app.exceptions import ContainerError
from dev_project.inside_docker_app import run_pre_commit


class ParseProjectDirTests(unittest.TestCase):
    def test_parses_directory_after_separator(self):
        self.assertEqual(
            run_pre_commit.parse_project_dir(
                ["--", "/home/odoo/extra-addons/project"]
            ),
            "/home/odoo/extra-addons/project",
        )

    def test_parses_directory_without_separator(self):
        self.assertEqual(
            run_pre_commit.parse_project_dir(["/home/odoo/project"]),
            "/home/odoo/project",
        )

    def test_rejects_missing_directory(self):
        with self.assertRaises(ContainerError):
            run_pre_commit.parse_project_dir(["--"])

    def test_rejects_multiple_directories(self):
        with self.assertRaises(ContainerError):
            run_pre_commit.parse_project_dir(
                ["--", "/home/odoo/a", "/home/odoo/b"]
            )


class RunPreCommitTests(unittest.TestCase):
    @patch("dev_project.inside_docker_app.run_pre_commit.run_logged")
    def test_runs_git_safe_directory_then_pre_commit_in_project_dir(
        self, mock_run_logged
    ):
        mock_run_logged.side_effect = [0, 0, 0]
        project_dir = "/home/odoo/extra-addons/project"

        run_pre_commit.run_pre_commit(project_dir)

        self.assertEqual(mock_run_logged.call_count, 3)
        wildcard_call = mock_run_logged.call_args_list[0]
        self.assertEqual(
            wildcard_call.args[0],
            [
                "git",
                "config",
                "--global",
                "--add",
                "safe.directory",
                "*",
            ],
        )
        self.assertEqual(wildcard_call.kwargs["cwd"], project_dir)

        project_call = mock_run_logged.call_args_list[1]
        self.assertEqual(
            project_call.args[0],
            [
                "git",
                "config",
                "--global",
                "--add",
                "safe.directory",
                project_dir,
            ],
        )
        self.assertEqual(project_call.kwargs["cwd"], project_dir)

        pre_commit_call = mock_run_logged.call_args_list[2]
        self.assertEqual(
            pre_commit_call.args[0],
            ["pre-commit", "run", "--all-files"],
        )
        self.assertEqual(pre_commit_call.kwargs["cwd"], project_dir)

    @patch("dev_project.inside_docker_app.run_pre_commit.run_logged")
    def test_git_config_failure_raises_container_error(self, mock_run_logged):
        mock_run_logged.return_value = 128

        with self.assertRaises(ContainerError):
            run_pre_commit.run_pre_commit("/home/odoo/project")

    @patch("dev_project.inside_docker_app.run_pre_commit.run_logged")
    def test_pre_commit_failure_exits_with_tool_exit_code(self, mock_run_logged):
        mock_run_logged.side_effect = [0, 0, 1]

        with self.assertRaises(SystemExit) as ctx:
            run_pre_commit.run_pre_commit("/home/odoo/project")

        self.assertEqual(ctx.exception.code, 1)


class RunPreCommitMainTests(unittest.TestCase):
    @patch("dev_project.inside_docker_app.run_pre_commit.parse_project_dir", return_value="/p")
    @patch("dev_project.inside_docker_app.run_pre_commit.run_pre_commit")
    @patch("dev_project.inside_docker_app.run_pre_commit._logger")
    def test_main_logs_container_error_and_exits(
        self, mock_logger, mock_run, _mock_parse
    ):
        mock_run.side_effect = ContainerError("git config failed")

        with self.assertRaises(SystemExit) as ctx:
            run_pre_commit.main()

        self.assertEqual(ctx.exception.code, 1)
        mock_logger.error.assert_called_once()

    @patch("dev_project.inside_docker_app.run_pre_commit.parse_project_dir", return_value="/p")
    @patch("dev_project.inside_docker_app.run_pre_commit.run_pre_commit")
    @patch("dev_project.inside_docker_app.run_pre_commit._logger")
    def test_main_logs_pre_commit_nonzero_exit(
        self, mock_logger, mock_run, _mock_parse
    ):
        mock_run.side_effect = SystemExit(2)

        with self.assertRaises(SystemExit) as ctx:
            run_pre_commit.main()

        self.assertEqual(ctx.exception.code, 2)
        mock_logger.error.assert_called_once_with("pre-commit exited with code %s", 2)

    @patch("dev_project.inside_docker_app.run_pre_commit.parse_project_dir", return_value="/p")
    @patch("dev_project.inside_docker_app.run_pre_commit.run_pre_commit")
    @patch("dev_project.inside_docker_app.run_pre_commit._logger")
    def test_main_logs_unexpected_exception_and_exits(
        self, mock_logger, mock_run, _mock_parse
    ):
        mock_run.side_effect = ValueError("unexpected")

        with self.assertRaises(SystemExit) as ctx:
            run_pre_commit.main()

        self.assertEqual(ctx.exception.code, 1)
        mock_logger.exception.assert_called_once_with("run_pre_commit failed")


if __name__ == "__main__":
    unittest.main()
