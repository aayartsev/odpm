"""Compose stack probe helpers for odpm --plan runtime steps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .compose.runtime import should_force_recreate_compose
from .host.cli.args import OdpmCliArgs
from .host.context import HostProjectContext

if TYPE_CHECKING:
    from .config import Config

PLAN_NO_DOCKER_WARNING = (
    "Compose stack health was not probed; --force-recreate is unknown"
)


def plan_probes_compose_stack(args: OdpmCliArgs) -> bool:
    return not args.plan_no_docker


def compose_up_would_run(args: OdpmCliArgs, host_ctx: HostProjectContext) -> bool:
    if args.skip_start:
        return False
    if host_ctx.update_lock:
        return False
    if args.build_image:
        return False
    return True


def compose_up_force_recreate_value(
    config: Config, args: OdpmCliArgs
) -> bool | None:
    """Return probe result, or None when recreate cannot be determined."""
    if not plan_probes_compose_stack(args):
        return None
    compose_cmd = getattr(config, "docker_compose_command", "")
    if not isinstance(compose_cmd, str) or not compose_cmd.strip():
        return None
    return should_force_recreate_compose(config)


def evaluate_compose_up_plan(
    config: Config, args: OdpmCliArgs
) -> tuple[str, tuple[str, ...]]:
    if not plan_probes_compose_stack(args):
        return (
            "start compose stack (--force-recreate unknown without docker probe)",
            (PLAN_NO_DOCKER_WARNING,),
        )
    compose_cmd = getattr(config, "docker_compose_command", "")
    if not isinstance(compose_cmd, str) or not compose_cmd.strip():
        return (
            "start compose stack (--force-recreate unknown; docker compose command unset)",
            ("Docker compose command is not configured; stack health was not probed",),
        )
    if should_force_recreate_compose(config):
        return (
            "start compose stack with --force-recreate (stack missing or unhealthy)",
            (),
        )
    return (
        "start compose stack without --force-recreate (stack healthy)",
        (),
    )
