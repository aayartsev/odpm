"""Structured container start command for docker compose."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .. import constants

StartCommandKind = Literal["standard", "pre_commit"]


@dataclass
class ComposeOdooService:
    working_dir: str
    command: list[str]
    include_runtime_config: bool = True


@dataclass
class StartCommand:
    """Logical start command for the odoo compose service."""

    kind: StartCommandKind = "standard"
    odoo_bin: list[str] = field(default_factory=list)
    docker_project_dir: str = ""
    pre_commit_project_dir: str = ""
    run_mode: str = constants.RUN_MODE_ODOO

    def to_compose_service(
        self, *, include_runtime_config: bool | None = None
    ) -> ComposeOdooService:
        if self.kind == "pre_commit":
            project_dir = self.pre_commit_project_dir or "/home/odoo"
            return ComposeOdooService(
                working_dir=project_dir,
                include_runtime_config=False,
                command=[
                    "python3",
                    "-m",
                    constants.RUN_PRE_COMMIT_ENTRYPOINT,
                    "--",
                    project_dir,
                ],
            )

        command = [
            "python3",
            "-m",
            constants.RUN_ODOO_ENTRYPOINT,
            "--",
            *self.odoo_bin,
        ]
        mount_runtime_config = (
            True if include_runtime_config is None else include_runtime_config
        )
        return ComposeOdooService(
            working_dir=self.docker_project_dir,
            include_runtime_config=mount_runtime_config,
            command=command,
        )
