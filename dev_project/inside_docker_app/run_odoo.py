"""Bootstrap container state and exec odoo-bin (replaces bash -c pipeline)."""

from __future__ import annotations

import os
import sys
from pathlib import PurePosixPath

from .. import constants
from ..scenario_policy import ScenarioPolicy
from .container_bootstrap import decode_config, run_container_bootstrap
from .exceptions import ContainerError


def read_config_from_env() -> dict:
    config_b64 = os.environ.get(constants.ODPM_CONFIG_B64_ENV, "").strip()
    if not config_b64:
        raise ContainerError(
            f"Missing required environment variable {constants.ODPM_CONFIG_B64_ENV}"
        )
    return decode_config(config_b64)


def parse_odoo_argv(argv: list[str] | None = None) -> list[str]:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--" in args:
        separator_index = args.index("--")
        return args[separator_index + 1 :]
    return args


def should_bootstrap_only(odoo_argv: list[str]) -> bool:
    if not odoo_argv:
        return False
    if odoo_argv == ["exit", "0"]:
        return True
    if len(odoo_argv) == 1 and odoo_argv[0] == "exit 0":
        return True
    return False


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
    config = read_config_from_env()
    odoo_argv = parse_odoo_argv(argv)
    run_container_bootstrap(config)
    if should_bootstrap_only(odoo_argv):
        raise SystemExit(0)
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
