"""Tests for pydevd_connect container launcher."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.debugger.constants import DEBUGGER_BACKEND_PYDEVD_CONNECT
from dev_project.inside_docker_app.exceptions import ContainerError
from dev_project.inside_docker_app import run_with_pydevd

from tests.container_config_helpers import minimal_container_config_dict


class RunWithPydevdTests(unittest.TestCase):
    def _write_config_file(self, **overrides) -> str:
        payload = minimal_container_config_dict(**overrides)
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        Path(path).write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path

    def tearDown(self) -> None:
        os.environ.pop(constants.ODPM_CONFIG_PATH_ENV, None)

    def test_attach_pydevd_debugger_calls_settrace(self) -> None:
        mock_pydevd = MagicMock()
        with patch.dict(
            "sys.modules",
            {"pydevd_pycharm": mock_pydevd},
        ):
            run_with_pydevd.attach_pydevd_debugger(
                connect_host="host.docker.internal",
                port=5678,
                suspend=True,
            )
        mock_pydevd.settrace.assert_called_once_with(
            "host.docker.internal",
            port=5678,
            suspend=True,
            stdout_to_server=True,
            stderr_to_server=True,
        )

    def test_attach_pydevd_debugger_connection_error_raises_container_error(
        self,
    ) -> None:
        mock_pydevd = MagicMock()
        mock_pydevd.settrace.side_effect = ConnectionRefusedError(
            "[Errno 111] Connection refused"
        )
        with patch.dict("sys.modules", {"pydevd_pycharm": mock_pydevd}):
            with self.assertRaises(ContainerError) as ctx:
                run_with_pydevd.attach_pydevd_debugger(
                    connect_host="host.docker.internal",
                    port=5678,
                    suspend=False,
                )
        message = str(ctx.exception)
        self.assertIn("host.docker.internal:5678", message)
        self.assertIn("Odoo Debug Server", message)

    @patch("dev_project.inside_docker_app.run_with_pydevd._logger")
    def test_attach_pydevd_debugger_logs_connecting_phase(self, mock_logger) -> None:
        mock_pydevd = MagicMock()
        with patch.dict("sys.modules", {"pydevd_pycharm": mock_pydevd}):
            run_with_pydevd.attach_pydevd_debugger(
                connect_host="host.docker.internal",
                port=5678,
                suspend=True,
            )
        mock_logger.info.assert_called_once()
        self.assertIn("host.docker.internal", mock_logger.info.call_args.args[1])

    def test_attach_pydevd_debugger_requires_package(self) -> None:
        import builtins

        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "pydevd_pycharm":
                raise ImportError("No module named 'pydevd_pycharm'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=guarded_import):
            with self.assertRaises(ContainerError) as ctx:
                run_with_pydevd.attach_pydevd_debugger(
                    connect_host="host.docker.internal",
                    port=5678,
                    suspend=False,
                )
        self.assertIn("pydevd-pycharm", str(ctx.exception))

    @patch("dev_project.inside_docker_app.run_with_pydevd.run_odoo_script_in_process")
    @patch("dev_project.inside_docker_app.run_with_pydevd.attach_pydevd_debugger")
    @patch("dev_project.inside_docker_app.run_with_pydevd.run_container_bootstrap")
    def test_run_with_pydevd_runs_odoo_in_process_after_settrace(
        self,
        mock_bootstrap,
        mock_attach,
        mock_run_odoo,
    ) -> None:
        path = self._write_config_file(
            debugger={
                "backend": DEBUGGER_BACKEND_PYDEVD_CONNECT,
                "port": 5678,
                "connect_host": "host.docker.internal",
                "suspend_on_connect": True,
            }
        )
        os.environ[constants.ODPM_CONFIG_PATH_ENV] = path
        run_with_pydevd.run_with_pydevd(
            ["--", "/home/odoo/odoo/odoo-bin", "-d", "demo"]
        )
        mock_bootstrap.assert_called_once()
        mock_attach.assert_called_once_with(
            connect_host="host.docker.internal",
            port=5678,
            suspend=True,
        )
        mock_run_odoo.assert_called_once_with(
            ["/home/odoo/odoo/odoo-bin", "-d", "demo"]
        )

    def test_run_odoo_script_in_process_uses_runpy_and_sys_argv(self) -> None:
        odoo_argv = ["/home/odoo/odoo/odoo-bin", "-d", "demo"]
        with patch("dev_project.inside_docker_app.run_with_pydevd.runpy.run_path") as mock_run_path:
            run_with_pydevd.run_odoo_script_in_process(odoo_argv)
        self.assertEqual(sys.argv, odoo_argv)
        mock_run_path.assert_called_once_with(
            "/home/odoo/odoo/odoo-bin",
            run_name="__main__",
        )

    @patch("dev_project.inside_docker_app.run_with_pydevd.run_container_bootstrap")
    def test_run_with_pydevd_rejects_debugpy_listen_backend(
        self, mock_bootstrap
    ) -> None:
        path = self._write_config_file(
            debugger={
                "backend": "debugpy_listen",
                "port": 5678,
                "connect_host": "host.docker.internal",
                "suspend_on_connect": False,
            }
        )
        os.environ[constants.ODPM_CONFIG_PATH_ENV] = path
        with self.assertRaises(ContainerError) as ctx:
            run_with_pydevd.run_with_pydevd(["--", "/home/odoo/odoo/odoo-bin"])
        self.assertIn("pydevd_connect", str(ctx.exception))
        mock_bootstrap.assert_called_once()

    @patch("dev_project.inside_docker_app.run_with_pydevd.run_with_pydevd")
    @patch("dev_project.inside_docker_app.run_with_pydevd._logger")
    def test_main_logs_container_error_and_exits(
        self, mock_logger, mock_run
    ) -> None:
        mock_run.side_effect = ContainerError("bootstrap failed")
        with self.assertRaises(SystemExit) as ctx:
            run_with_pydevd.main()
        self.assertEqual(ctx.exception.code, 1)
        mock_logger.error.assert_called_once()

    @patch("dev_project.inside_docker_app.run_with_pydevd.run_with_pydevd")
    @patch("dev_project.inside_docker_app.run_with_pydevd._logger")
    def test_main_logs_unexpected_exception_and_exits(
        self, mock_logger, mock_run
    ) -> None:
        mock_run.side_effect = ValueError("unexpected")
        with self.assertRaises(SystemExit) as ctx:
            run_with_pydevd.main()
        self.assertEqual(ctx.exception.code, 1)
        mock_logger.exception.assert_called_once_with("run_with_pydevd failed")


if __name__ == "__main__":
    unittest.main()
