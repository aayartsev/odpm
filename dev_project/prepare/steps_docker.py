"""Docker engine prepare steps."""

from __future__ import annotations

from ..plan import PlanStep
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_docker_engine_check(ctx: PrepareContext) -> PlanStep:
    description = "Check Docker engine and running odpm containers"
    reason = (
        "verify Docker engine and containers"
        if ctx.config.check_system
        else "check_system disabled; step still runs for compatibility"
    )
    return make_plan_step(
        "docker.engine.check",
        description,
        "run",
        ctx.config.check_system,
        reason,
    )


def exec_docker_engine_check(ctx: PrepareContext) -> None:
    ctx.system_checker.check_docker()
    ctx.system_checker.check_running_containers()
