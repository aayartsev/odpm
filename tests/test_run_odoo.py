import json
import os
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from dev_project import constants
from dev_project.container_config import load_container_config_from_env
from dev_project.inside_docker_app.exceptions import ContainerError
from dev_project.inside_docker_app import run_odoo

from tests.container_config_helpers import (
    minimal_container_config,
    minimal_container_config_dict,
)


class RunOdooTests(unittest.TestCase):
    def _write_config_file(self, **overrides) -> str:
        payload = minimal_container_config_dict(**overrides)
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        Path(path).write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path

    def tearDown(self) -> None:
        os.environ.pop(constants.ODPM_CONFIG_PATH_ENV, None)

    def test_read_config_from_file(self):
        path = self._write_config_file(odpm_scenario=constants.SERVER_SCENARIO)
        os.environ[constants.ODPM_CONFIG_PATH_ENV] = path
        config = load_container_config_from_env()
        self.assertEqual(config.odpm_scenario, constants.SERVER_SCENARIO)

    def test_read_config_requires_file(self):
        with self.assertRaises(ContainerError):
            load_container_config_from_env()

    def test_parse_odoo_argv_after_separator(self):
        self.assertEqual(
            run_odoo.parse_odoo_argv(
                ["--", "/home/odoo/odoo/odoo-bin", "-d", "demo"]
            ),
            ["/home/odoo/odoo/odoo-bin", "-d", "demo"],
        )

    def test_should_bootstrap_only_from_run_mode(self):
        self.assertTrue(
            run_odoo.should_bootstrap_only(
                minimal_container_config(run_mode=constants.RUN_MODE_BOOTSTRAP_ONLY)
            )
        )
        self.assertFalse(
            run_odoo.should_bootstrap_only(
                minimal_container_config(run_mode=constants.RUN_MODE_ODOO)
            )
        )

    def test_build_odoo_exec_argv_includes_debugpy_for_developer(self):
        config = minimal_container_config(odpm_scenario=constants.DEVELOPER_SCENARIO)
        exec_argv = run_odoo.build_odoo_exec_argv(
            config,
            ["/home/odoo/odoo/odoo-bin", "-d", "demo"],
        )
        self.assertEqual(exec_argv[0], "/home/odoo/.venv/bin/python3")
        self.assertIn("debugpy", exec_argv)

    def test_build_odoo_exec_argv_without_debugpy_for_server(self):
        config = minimal_container_config(odpm_scenario=constants.SERVER_SCENARIO)
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
        path = self._write_config_file(odpm_scenario=constants.SERVER_SCENARIO)
        os.environ[constants.ODPM_CONFIG_PATH_ENV] = path
        run_odoo.run_odoo(["--", "/home/odoo/odoo/odoo-bin", "-d", "demo"])
        mock_bootstrap.assert_called_once()
        mock_chdir.assert_not_called()
        exec_argv = mock_execv.call_args[0][1]
        self.assertEqual(exec_argv[0], "/home/odoo/.venv/bin/python3")
        self.assertEqual(exec_argv[-2:], ["-d", "demo"])

    @patch("dev_project.inside_docker_app.run_odoo.run_container_bootstrap")
    def test_run_odoo_bootstrap_only_exits_without_exec(self, mock_bootstrap):
        path = self._write_config_file(
            odpm_scenario=constants.CI_SCENARIO,
            run_mode=constants.RUN_MODE_BOOTSTRAP_ONLY,
            venv_mode=constants.VENV_MODE_BAKED,
        )
        os.environ[constants.ODPM_CONFIG_PATH_ENV] = path
        with self.assertRaises(SystemExit) as ctx:
            run_odoo.run_odoo(["--"])
        self.assertEqual(ctx.exception.code, 0)
        mock_bootstrap.assert_called_once()


class MainEntrypointTests(unittest.TestCase):
    def test_main_import_emits_deprecation_warning(self):
        import importlib
        import sys

        sys.modules.pop("dev_project.inside_docker_app.main", None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.import_module("dev_project.inside_docker_app.main")
        self.assertTrue(
            any(issubclass(item.category, DeprecationWarning) for item in caught)
        )

    @patch("dev_project.inside_docker_app.run_odoo.main")
    def test_main_module_delegates_to_run_odoo(self, mock_run_odoo_main):
        import importlib
        import sys

        sys.modules.pop("dev_project.inside_docker_app.main", None)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            main_module = importlib.import_module("dev_project.inside_docker_app.main")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            main_module.main()
        mock_run_odoo_main.assert_called_once()


if __name__ == "__main__":
    unittest.main()
