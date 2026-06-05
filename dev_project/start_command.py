"""Structured container start command for docker compose."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Literal

from . import constants
from .inside_docker_app import cli_params

StartCommandKind = Literal["standard", "pip_install", "pre_commit"]


@dataclass
class StartCommand:
    """Logical start command; ``to_compose_shell()`` is the only shell string builder."""

    kind: StartCommandKind = "standard"
    entrypoint: list[str] = field(default_factory=list)
    config_b64: str = ""
    odoo_bin: list[str] = field(default_factory=list)
    debugpy: bool = False
    docker_project_dir: str = ""
    docker_venv_dir: str = ""
    debugger_port: int = constants.DEBUGGER_DOCKER_PORT
    pip_install_script: str = ""
    pre_commit_script: str = ""
    odoo_shell_override: str | None = None

    def to_compose_shell(self) -> str:
        if self.kind == "pip_install":
            return f"bash -c '{self.pip_install_script}'"
        if self.kind == "pre_commit":
            return f"/bin/bash -c '{self.pre_commit_script}'"

        entrypoint_invocation = " ".join(self.entrypoint)
        if self.odoo_shell_override is not None:
            odoo_command = self.odoo_shell_override
        else:
            odoo_tokens = ["python3", "-u"]
            if self.debugpy:
                odoo_tokens.extend(
                    [
                        "-m",
                        "debugpy",
                        "--listen",
                        f"0.0.0.0:{self.debugger_port}",
                    ]
                )
            odoo_tokens.extend(self.odoo_bin)
            odoo_command = " ".join(odoo_tokens)

        start_main = " && ".join(
            [
                f"cd {self.docker_project_dir}",
                (
                    f"{entrypoint_invocation} "
                    f"{cli_params.CONFIG_BASE64_DATA} {self.config_b64}"
                ),
                f". {pathlib.PurePosixPath(self.docker_venv_dir, 'bin', 'activate')}",
                odoo_command,
            ]
        )
        return f"bash -c '{start_main}'"
