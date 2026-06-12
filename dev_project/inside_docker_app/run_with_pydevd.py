"""Bootstrap container state, attach pydevd to IDE Debug Server, run odoo-bin in-process."""

from __future__ import annotations

import runpy
import sys

from ..container_config import load_container_config_from_env
from ..debugger.constants import DEBUGGER_BACKEND_PYDEVD_CONNECT
from .container_bootstrap import run_container_bootstrap
from .exceptions import ContainerError
from .run_odoo import parse_odoo_argv, should_bootstrap_only


def _require_pydevd_settings(config) -> tuple[str, int, bool]:
    settings = config.debugger
    if settings is None:
        raise ContainerError("Missing debugger settings for pydevd_connect")
    if settings.backend != DEBUGGER_BACKEND_PYDEVD_CONNECT:
        raise ContainerError(
            f"run_with_pydevd requires debugger.backend={DEBUGGER_BACKEND_PYDEVD_CONNECT!r}, "
            f"got {settings.backend!r}"
        )
    return settings.connect_host, settings.port, settings.suspend_on_connect


def attach_pydevd_debugger(*, connect_host: str, port: int, suspend: bool) -> None:
    try:
        import pydevd_pycharm
    except ImportError as exc:
        raise ContainerError(
            "pydevd-pycharm is not installed in the container venv"
        ) from exc
    pydevd_pycharm.settrace(
        connect_host,
        port=port,
        suspend=suspend,
        stdout_to_server=True,
        stderr_to_server=True,
    )


def run_odoo_script_in_process(odoo_argv: list[str]) -> None:
    """Run odoo-bin in the current interpreter after pydevd settrace."""
    if not odoo_argv:
        raise ContainerError("Missing odoo-bin argv")
    sys.argv = list(odoo_argv)
    runpy.run_path(odoo_argv[0], run_name="__main__")


def run_with_pydevd(argv: list[str] | None = None) -> None:
    config = load_container_config_from_env()
    odoo_argv = parse_odoo_argv(argv)
    run_container_bootstrap(config)
    if should_bootstrap_only(config):
        raise SystemExit(0)
    if not odoo_argv:
        raise ContainerError("Missing odoo-bin argv after bootstrap")

    connect_host, port, suspend = _require_pydevd_settings(config)
    attach_pydevd_debugger(connect_host=connect_host, port=port, suspend=suspend)
    run_odoo_script_in_process(odoo_argv)


def main() -> None:
    try:
        run_with_pydevd()
    except ContainerError as exc:
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
