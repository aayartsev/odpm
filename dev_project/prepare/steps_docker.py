"""Docker engine prepare steps."""

from __future__ import annotations

from ..plan import PlanStep
from ..plan.l10n import plan_msg
from ..system_check_policy import SystemCheckPolicy
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_docker_engine_check(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Check Docker engine")
    policy = SystemCheckPolicy.from_host_context(ctx.host_ctx)
    if not policy.beginner_docker:
        return make_plan_step(
            "docker.engine.check",
            description,
            "skip",
            False,
            plan_msg("check_system disabled; Docker check skipped"),
        )
    if policy.skip_docker_daemon and policy.skip_ensure_base_local:
        return make_plan_step(
            "docker.engine.check",
            description,
            "skip",
            False,
            plan_msg("CI kaniko direct prepare-only; Docker daemon check skipped"),
        )
    return make_plan_step(
        "docker.engine.check",
        description,
        "run",
        True,
        plan_msg("verify Docker engine"),
    )


def exec_docker_engine_check(ctx: PrepareContext) -> None:
    ctx.system_checker.check_docker()


def evaluate_docker_ports_release(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Stop containers occupying odpm ports")
    policy = SystemCheckPolicy.from_host_context(ctx.host_ctx)
    if not policy.developer_port_release:
        return make_plan_step(
            "docker.ports.release",
            description,
            "skip",
            False,
            plan_msg("port release runs only in developer scenario"),
        )
    return make_plan_step(
        "docker.ports.release",
        description,
        "run",
        False,
        plan_msg("free odoo, debugger, postgres, and gevent ports before compose up"),
    )


def exec_docker_ports_release(ctx: PrepareContext) -> None:
    ctx.system_checker.check_running_containers()
