import base64
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.inside_docker_app.exceptions import ContainerError
from dev_project.inside_docker_app import run_odoo
from dev_project.scenario_policy import ScenarioPolicy


class RunOdooTests(unittest.TestCase):
    def _config_payload(self, scenario: str) -> dict:
        return {
            "docker_venv_dir": "/home/odoo/.venv",
            "docker_project_dir": "/home/odoo",
            "odpm_scenario": scenario,
        }

    def _set_config_env(self, scenario: str) -> None:
        payload = self._config_payload(scenario)
        os.environ[constants.ODPM_CONFIG_B64_ENV] = base64.b64encode(
            json.dumps(payload).encode("utf-8")
        ).decode("ascii")

    def tearDown(self) -> None:
        os.environ.pop(constants.ODPM_CONFIG_B64_ENV, None)

    def test_read_config_from_env_requires_variable(self):
        os.environ.pop(constants.ODPM_CONFIG_B64_ENV, None)
        with self.assertRaises(ContainerError):
            run_odoo.read_config_from_env()

    def test_parse_odoo_argv_after_separator(self):
        self.assertEqual(
            run_odoo.parse_odoo_argv(
                ["--", "/home/odoo/odoo/odoo-bin", "-d", "demo"]
            ),
            ["/home/odoo/odoo/odoo-bin", "-d", "demo"],
        )

    def test_should_bootstrap_only_for_exit_zero(self):
        self.assertTrue(run_odoo.should_bootstrap_only(["exit", "0"]))
        self.assertFalse(run_odoo.should_bootstrap_only(["/home/odoo/odoo/odoo-bin"]))

    def test_build_odoo_exec_argv_includes_debugpy_for_developer(self):
        config = self._config_payload(constants.DEVELOPER_SCENARIO)
        exec_argv = run_odoo.build_odoo_exec_argv(
            config,
            ["/home/odoo/odoo/odoo-bin", "-d", "demo"],
        )
        self.assertEqual(exec_argv[0], "/home/odoo/.venv/bin/python3")
        self.assertIn("-m", exec_argv)
        self.assertIn("debugpy", exec_argv)
        self.assertEqual(exec_argv[-1], "demo")

    def test_build_odoo_exec_argv_without_debugpy_for_server(self):
        config = self._config_payload(constants.SERVER_SCENARIO)
        exec_argv = run_odoo.build_odoo_exec_argv(
            config,
            ["/home/odoo/odoo/odoo-bin"],
        )
        self.assertNotIn("debugpy", exec_argv)

    @patch("dev_project.inside_docker_app.run_odoo.os.execv")
    @patch("dev_project.inside_docker_app.run_odoo.os.chdir")
    @patch("dev_project.inside_docker_app.run_odoo.run_container_bootstrap")
    def test_run_odoo_execs_venv_python_with_odoo_argv(
        self, mock_bootstrap, mock_chdir, mock_execv
    ):
        self._set_config_env(constants.SERVER_SCENARIO)
        run_odoo.run_odoo(["--", "/home/odoo/odoo/odoo-bin", "-d", "demo"])
        mock_bootstrap.assert_called_once()
        mock_chdir.assert_called_once_with("/home/odoo")
        exec_argv = mock_execv.call_args[0][1]
        self.assertEqual(exec_argv[0], "/home/odoo/.venv/bin/python3")
        self.assertEqual(exec_argv[-2:], ["-d", "demo"])

    @patch("dev_project.inside_docker_app.run_odoo.run_container_bootstrap")
    def test_run_odoo_bootstrap_only_exits_without_exec(self, mock_bootstrap):
        self._set_config_env(constants.CI_SCENARIO)
        with self.assertRaises(SystemExit) as ctx:
            run_odoo.run_odoo(["--", "exit", "0"])
        self.assertEqual(ctx.exception.code, 0)
        mock_bootstrap.assert_called_once()


if __name__ == "__main__":
    unittest.main()
