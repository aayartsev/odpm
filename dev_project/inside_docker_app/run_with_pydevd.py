"""Bootstrap container state, attach pydevd to IDE Debug Server, run odoo-bin in-process."""

from __future__ import annotations

import runpy
import sys

from ..container_config import load_container_config_from_env
from ..debugger.constants import DEBUGGER_BACKEND_PYDEVD_CONNECT
from ..logging import get_module_logger
from .container_bootstrap import run_container_bootstrap
from .exceptions import ContainerError
from .run_odoo import parse_odoo_argv, should_bootstrap_only

_logger = get_module_logger(__name__)

_PYDEVD_CONNECT_HINT = (
    "Start the Odoo Debug Server run configuration in PyCharm Professional "
    "(Run, not Attach) and wait for 'Waiting for process connection...' "
    "before starting the container."
)


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


def _pydevd_connect_error_message(connect_host: str, port: int) -> str:
    return (
        f"Could not connect to PyCharm Debug Server at {connect_host}:{port}. "
        f"{_PYDEVD_CONNECT_HINT}"
    )


def attach_pydevd_debugger(*, connect_host: str, port: int, suspend: bool) -> None:
    try:
        import pydevd_pycharm
    except ImportError as exc:
        raise ContainerError(
            "pydevd-pycharm is not installed in the container venv"
        ) from exc
    _logger.info(
        "Connecting to PyCharm Debug Server at %s:%s (suspend=%s)...",
        connect_host,
        port,
        suspend,
    )
    try:
        pydevd_pycharm.settrace(
            connect_host,
            port=port,
            suspend=suspend,
            stdout_to_server=True,
            stderr_to_server=True,
        )
    except (OSError, RuntimeError, TimeoutError) as exc:
        raise ContainerError(
            _pydevd_connect_error_message(connect_host, port)
        ) from exc


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
        _logger.error("%s", exc)
        sys.exit(exc.exit_code)
    except Exception:
        _logger.exception("run_with_pydevd failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
