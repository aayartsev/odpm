"""Tests for debugger backend registry and resolve."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.debugger.backends import get_backend
from dev_project.debugger.constants import DEBUGGER_BACKEND_PYDEVD_CONNECT
from dev_project.debugger.exec_settings import DebuggerExecSettings
from dev_project.debugger.resolve import resolve_debugger_backend
from dev_project.inside_docker_app import run_odoo

from tests.container_config_helpers import minimal_container_config


class DebuggerBackendsTests(unittest.TestCase):
    def test_debugpy_listen_wrap_exec_argv(self) -> None:
        backend = get_backend("debugpy_listen")
        exec_argv = backend.wrap_exec_argv(
            "/home/odoo/.venv/bin/python3",
            ["/home/odoo/odoo/odoo-bin", "-d", "demo"],
            settings=DebuggerExecSettings(port=5678),
        )
        self.assertEqual(exec_argv[0], "/home/odoo/.venv/bin/python3")
        self.assertIn("debugpy", exec_argv)
        self.assertIn("0.0.0.0:5678", exec_argv)
        self.assertEqual(exec_argv[-2:], ["-d", "demo"])

    def test_resolve_returns_none_without_debugger_settings(self) -> None:
        config = minimal_container_config(
            odpm_scenario=constants.SERVER_SCENARIO,
            debugger=None,
        )
        self.assertIsNone(resolve_debugger_backend(config))

    def test_build_odoo_exec_argv_uses_backend_settings_port(self) -> None:
        config = minimal_container_config(
            debugger={
                "backend": "debugpy_listen",
                "port": 9999,
                "connect_host": "host.docker.internal",
                "suspend_on_connect": False,
            }
        )
        exec_argv = run_odoo.build_odoo_exec_argv(
            config,
            ["/home/odoo/odoo/odoo-bin"],
        )
        self.assertIn("0.0.0.0:9999", exec_argv)

    def test_pydevd_connect_wrap_exec_argv_uses_launcher_module(self) -> None:
        backend = get_backend(DEBUGGER_BACKEND_PYDEVD_CONNECT)
        exec_argv = backend.wrap_exec_argv(
            "/home/odoo/.venv/bin/python3",
            ["/home/odoo/odoo/odoo-bin", "-d", "demo"],
            settings=DebuggerExecSettings(
                port=5678,
                connect_host="host.docker.internal",
                suspend_on_connect=True,
            ),
        )
        self.assertEqual(
            exec_argv[:5],
            [
                "/home/odoo/.venv/bin/python3",
                "-u",
                "-m",
                "dev_project.inside_docker_app.run_with_pydevd",
                "--",
            ],
        )
        self.assertEqual(exec_argv[-2:], ["-d", "demo"])

    def test_pydevd_connect_does_not_publish_compose_port(self) -> None:
        backend = get_backend(DEBUGGER_BACKEND_PYDEVD_CONNECT)
        self.assertFalse(backend.needs_compose_port_publish)

    def test_pydevd_connect_pip_requirement(self) -> None:
        backend = get_backend(DEBUGGER_BACKEND_PYDEVD_CONNECT)
        self.assertEqual(
            backend.pip_requirement("3.12"),
            constants.PYDEVD_PYCHARM["3.12"],
        )

    def test_build_odoo_exec_argv_pydevd_connect_delegates_to_launcher(self) -> None:
        config = minimal_container_config(
            debugger={
                "backend": DEBUGGER_BACKEND_PYDEVD_CONNECT,
                "port": 5678,
                "connect_host": "host.docker.internal",
                "suspend_on_connect": False,
            }
        )
        exec_argv = run_odoo.build_odoo_exec_argv(
            config,
            ["/home/odoo/odoo/odoo-bin"],
        )
        self.assertIn("dev_project.inside_docker_app.run_with_pydevd", exec_argv)


if __name__ == "__main__":
    unittest.main()
