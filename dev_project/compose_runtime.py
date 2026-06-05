"""Docker Compose runtime helpers: stack health and up options."""

from __future__ import annotations

import shlex
import subprocess

from . import constants
from .host_config import Config

COMPOSE_STACK_SERVICES = ("odoo", constants.DATABASE_NAME_INSTANCE)


def _compose_base_argv(config: Config) -> list[str]:
    return shlex.split(config.docker_compose_command)


def _running_container_id(
    config: Config, service: str
) -> str | None:
    result = subprocess.run(
        _compose_base_argv(config) + ["ps", "-q", service],
        cwd=config.project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[0] if lines else None


def container_is_running_and_healthy(container_id: str) -> bool:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
            container_id,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    parts = result.stdout.strip().split()
    if not parts or parts[0] != "true":
        return False
    if len(parts) > 1 and parts[1] not in ("healthy", ""):
        return False
    return True


def compose_stack_is_healthy(config: Config) -> bool:
    """True when odoo and postgres compose services are up (and healthy if probed)."""
    for service in COMPOSE_STACK_SERVICES:
        container_id = _running_container_id(config, service)
        if not container_id:
            return False
        if not container_is_running_and_healthy(container_id):
            return False
    return True


def should_force_recreate_compose(config: Config) -> bool:
    """Recreate only when the stack is missing or not healthy."""
    return not compose_stack_is_healthy(config)
