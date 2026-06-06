"""Bootstrap container state and exec odoo-bin (replaces bash -c pipeline)."""

from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path, PurePosixPath

from .. import constants
from ..scenario_policy import ScenarioPolicy
from .container_bootstrap import decode_config, run_container_bootstrap
from .exceptions import ContainerError


def read_config_from_file(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def read_config_from_env_b64() -> dict:
    config_b64 = os.environ.get(constants.ODPM_CONFIG_B64_ENV, "").strip()
    if not config_b64:
        raise ContainerError(
            f"Missing required environment variable {constants.ODPM_CONFIG_B64_ENV}"
        )
    return decode_config(config_b64)


def read_config() -> dict:
    config_path = os.environ.get(
        constants.ODPM_CONFIG_PATH_ENV,
        constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH,
    )
    if os.path.isfile(config_path):
        return read_config_from_file(config_path)

    config_b64 = os.environ.get(constants.ODPM_CONFIG_B64_ENV, "").strip()
    if config_b64:
        warnings.warn(
            f"{constants.ODPM_CONFIG_B64_ENV} is deprecated; "
            f"mount runtime config at {constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}",
            DeprecationWarning,
            stacklevel=2,
        )
        return decode_config(config_b64)

    raise ContainerError(
        "Missing container config: expected "
        f"{constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH} "
        f"or deprecated {constants.ODPM_CONFIG_B64_ENV}"
    )


def parse_odoo_argv(argv: list[str] | None = None) -> list[str]:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--" in args:
        separator_index = args.index("--")
        return args[separator_index + 1 :]
    return args


def should_bootstrap_only(config: dict) -> bool:
    return config.get("run_mode") == constants.RUN_MODE_BOOTSTRAP_ONLY


def build_odoo_exec_argv(config: dict, odoo_argv: list[str]) -> list[str]:
    venv_python = str(
        PurePosixPath(config["docker_venv_dir"], "bin", "python3")
    )
    policy = ScenarioPolicy.from_scenario(config.get("odpm_scenario", ""))
    exec_argv = [venv_python, "-u"]
    if policy.include_debugpy:
        exec_argv.extend(
            [
                "-m",
                "debugpy",
                "--listen",
                f"0.0.0.0:{constants.DEBUGGER_DOCKER_PORT}",
            ]
        )
    exec_argv.extend(odoo_argv)
    return exec_argv


def run_odoo(argv: list[str] | None = None) -> None:
    config = read_config()
    odoo_argv = parse_odoo_argv(argv)
    run_container_bootstrap(config)
    if should_bootstrap_only(config):
        raise SystemExit(0)
    if not odoo_argv:
        raise ContainerError("Missing odoo-bin argv after bootstrap")
    exec_argv = build_odoo_exec_argv(config, odoo_argv)
    project_dir = config.get("docker_project_dir", "")
    if project_dir:
        os.chdir(project_dir)
    os.execv(exec_argv[0], exec_argv)


def main() -> None:
    from .exceptions import ContainerError

    try:
        run_odoo()
    except ContainerError as exc:
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
