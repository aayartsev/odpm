"""Docker Compose runtime helpers: stack health and up options."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from .. import constants

if TYPE_CHECKING:
    from ..config import Config
    from ..host.context import HostProjectContext

COMPOSE_ODOO_SERVICE = "odoo"


def compose_stack_services(config: Config) -> tuple[str, str]:
    """Return compose service names for stack health checks (odoo, postgres)."""
    return (COMPOSE_ODOO_SERVICE, config.user_env.postgres_service_name)


# Backward-compatible default pair when config is unavailable.
COMPOSE_STACK_SERVICES = (COMPOSE_ODOO_SERVICE, constants.DEFAULT_POSTGRES_SERVICE_NAME)


def _run_checked(*args, **kwargs):
    from ..subprocess_runner import run_checked

    return run_checked(*args, **kwargs)


def _compose_base_argv_for_host(host_ctx: HostProjectContext) -> list[str]:
    return shlex.split(host_ctx.docker_compose_command)


def _compose_base_argv(config: Config) -> list[str]:
    from ..host.context import HostProjectContext

    return _compose_base_argv_for_host(HostProjectContext.from_config(config))


def compose_service_container_id(config: Config, service: str) -> str | None:
    """Return the running container id for a compose service, or None."""
    return _running_container_id(config, service)


def _running_container_id_for_host(
    host_ctx: HostProjectContext, service: str
) -> str | None:
    result = _run_checked(
        _compose_base_argv_for_host(host_ctx) + ["ps", "-q", service],
        cwd=host_ctx.project_dir,
    )
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[0] if lines else None


def _running_container_id(
    config: Config, service: str
) -> str | None:
    from ..host.context import HostProjectContext

    return _running_container_id_for_host(HostProjectContext.from_config(config), service)


def container_is_running_and_healthy(container_id: str) -> bool:
    result = _run_checked(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
            container_id,
        ],
    )
    if result.returncode != 0:
        return False
    parts = result.stdout.strip().split()
    if not parts or parts[0] != "true":
        return False
    if len(parts) > 1 and parts[1] not in ("healthy", ""):
        return False
    return True


def compose_stack_is_healthy_for_host(host_ctx: HostProjectContext) -> bool:
    """True when odoo and postgres compose services are up (and healthy if probed)."""
    for service in (
        COMPOSE_ODOO_SERVICE,
        host_ctx.user_env.postgres_service_name,
    ):
        container_id = _running_container_id_for_host(host_ctx, service)
        if not container_id:
            return False
        if not container_is_running_and_healthy(container_id):
            return False
    return True


def compose_stack_is_healthy(config: Config) -> bool:
    """True when odoo and postgres compose services are up (and healthy if probed)."""
    from ..host.context import HostProjectContext

    return compose_stack_is_healthy_for_host(HostProjectContext.from_config(config))


def should_force_recreate_compose_for_host(host_ctx: HostProjectContext) -> bool:
    """Recreate only when the stack is missing or not healthy."""
    return not compose_stack_is_healthy_for_host(host_ctx)


def should_force_recreate_compose(config: Config) -> bool:
    """Recreate only when the stack is missing or not healthy."""
    from ..host.context import HostProjectContext

    return should_force_recreate_compose_for_host(HostProjectContext.from_config(config))
