"""Structured container start command for docker compose."""

from __future__ import annotations

import pathlib
import warnings
from dataclasses import dataclass, field
from typing import Literal

from . import constants
from .inside_docker_app import cli_params

StartCommandKind = Literal["standard", "pip_install", "pre_commit"]


@dataclass
class ComposeOdooService:
    working_dir: str
    config_b64: str
    command: list[str]
    include_config_env: bool = True


@dataclass
class StartCommand:
    """Logical start command for the odoo compose service."""

    kind: StartCommandKind = "standard"
    config_b64: str = ""
    odoo_bin: list[str] = field(default_factory=list)
    docker_project_dir: str = ""
    docker_venv_dir: str = ""
    pip_install_script: str = ""
    pre_commit_script: str = ""
    bootstrap_only: bool = False

    def to_compose_service(self) -> ComposeOdooService:
        if self.kind == "pip_install":
            return ComposeOdooService(
                working_dir=self.docker_project_dir or "/home/odoo",
                config_b64="",
                include_config_env=False,
                command=[
                    "/bin/bash",
                    "-c",
                    self.pip_install_script,
                ],
            )
        if self.kind == "pre_commit":
            return ComposeOdooService(
                working_dir=self.docker_project_dir or "/home/odoo",
                config_b64="",
                include_config_env=False,
                command=[
                    "/bin/bash",
                    "-c",
                    self.pre_commit_script,
                ],
            )

        odoo_argv = list(self.odoo_bin)
        if self.bootstrap_only:
            odoo_argv = ["exit", "0"]

        return ComposeOdooService(
            working_dir=self.docker_project_dir,
            config_b64=self.config_b64,
            include_config_env=True,
            command=[
                "python3",
                "-m",
                constants.RUN_ODOO_ENTRYPOINT,
                "--",
                *odoo_argv,
            ],
        )

    def to_compose_shell(self) -> str:
        warnings.warn(
            "StartCommand.to_compose_shell() is deprecated; use to_compose_service()",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.kind == "pip_install":
            return f"bash -c '{self.pip_install_script}'"
        if self.kind == "pre_commit":
            return f"/bin/bash -c '{self.pre_commit_script}'"

        entrypoint_invocation = f"python3 -m {constants.RUN_ODOO_ENTRYPOINT}"
        if self.bootstrap_only:
            odoo_command = "exit 0"
        else:
            odoo_tokens = list(self.odoo_bin)
            odoo_command = " ".join(odoo_tokens)

        start_main = " && ".join(
            [
                f"cd {self.docker_project_dir}",
                (
                    f"{entrypoint_invocation} "
                    f"{cli_params.CONFIG_BASE64_DATA} {self.config_b64}"
                ),
                f". {pathlib.PurePosixPath(self.docker_venv_dir, 'bin', 'activate')}",
                f"python3 -u {odoo_command}",
            ]
        )
        return f"bash -c '{start_main}'"
