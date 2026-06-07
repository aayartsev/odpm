"""Mutable host runtime state produced during prepare / system checks."""

from __future__ import annotations

from dataclasses import dataclass

from .. import constants
from ..start_command import ComposeOdooService


@dataclass
class HostRuntimeState:
    """Prepare-phase outputs and docker-compose runtime options."""

    compose_service: ComposeOdooService | None = None
    container_run_mode: str = constants.RUN_MODE_ODOO
    no_log_prefix: bool = False
    docker_compose_command: str | None = None

    def resolved_docker_compose_command(self, layout_default: str) -> str:
        if self.docker_compose_command is not None:
            return self.docker_compose_command
        return layout_default
