"""Compose stack probe helpers for odpm --plan runtime steps."""

from __future__ import annotations

from ..compose import runtime as compose_runtime
from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from .l10n import plan_msg

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


def probe_should_force_recreate(host_ctx: HostProjectContext) -> bool:
    """Plan-layer seam for compose health; unit tests patch this name."""
    return compose_runtime.should_force_recreate_compose_for_host(host_ctx)


def compose_up_force_recreate_value(
    host_ctx: HostProjectContext, args: OdpmCliArgs
) -> bool | None:
    """Return probe result, or None when recreate cannot be determined."""
    if not plan_probes_compose_stack(args):
        return None
    compose_cmd = host_ctx.docker_compose_command
    if not isinstance(compose_cmd, str) or not compose_cmd.strip():
        return None
    return probe_should_force_recreate(host_ctx)


def evaluate_compose_up_plan(
    host_ctx: HostProjectContext, args: OdpmCliArgs
) -> tuple[str, tuple[str, ...]]:
    if not plan_probes_compose_stack(args):
        return (
            plan_msg(
                "start compose stack (--force-recreate unknown without docker probe)"
            ),
            (plan_msg(PLAN_NO_DOCKER_WARNING),),
        )
    compose_cmd = host_ctx.docker_compose_command
    if not isinstance(compose_cmd, str) or not compose_cmd.strip():
        return (
            plan_msg(
                "start compose stack (--force-recreate unknown; docker compose command unset)"
            ),
            (
                plan_msg(
                    "Docker compose command is not configured; stack health was not probed"
                ),
            ),
        )
    if probe_should_force_recreate(host_ctx):
        return (
            plan_msg(
                "start compose stack with --force-recreate (stack missing or unhealthy)"
            ),
            (),
        )
    return (
        plan_msg(
            "start compose stack without --force-recreate (stack healthy)"
        ),
        (),
    )
