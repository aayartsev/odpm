"""Bootstrap container state and exec odoo-bin (replaces bash -c pipeline)."""

from __future__ import annotations

import os
import sys
from pathlib import PurePosixPath

from .. import constants
from ..container_config import ContainerConfig, load_container_config_from_env
from ..debugger.exec_settings import debugger_exec_settings_from_config
from ..debugger.resolve import resolve_debugger_backend
from ..logging import get_module_logger
from .container_bootstrap import run_container_bootstrap
from .exceptions import ContainerError

_logger = get_module_logger(__name__)


def parse_odoo_argv(argv: list[str] | None = None) -> list[str]:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--" in args:
        separator_index = args.index("--")
        return args[separator_index + 1 :]
    return args


def should_bootstrap_only(config: ContainerConfig) -> bool:
    return config.run_mode == constants.RUN_MODE_BOOTSTRAP_ONLY


def build_odoo_exec_argv(config: ContainerConfig, odoo_argv: list[str]) -> list[str]:
    venv_python = str(
        PurePosixPath(config.docker_venv_dir, "bin", "python3")
    )
    backend = resolve_debugger_backend(config)
    if backend is None:
        return [venv_python, "-u", *odoo_argv]
    return backend.wrap_exec_argv(
        venv_python,
        odoo_argv,
        settings=debugger_exec_settings_from_config(config),
    )


def run_odoo(argv: list[str] | None = None) -> None:
    config = load_container_config_from_env()
    odoo_argv = parse_odoo_argv(argv)
    run_container_bootstrap(config)
    if should_bootstrap_only(config):
        raise SystemExit(0)
    if not odoo_argv:
        raise ContainerError("Missing odoo-bin argv after bootstrap")
    exec_argv = build_odoo_exec_argv(config, odoo_argv)
    os.execv(exec_argv[0], exec_argv)


def main() -> None:
    try:
        run_odoo()
    except ContainerError as exc:
        _logger.error("%s", exc)
        sys.exit(exc.exit_code)
    except Exception:
        _logger.exception("run_odoo failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
