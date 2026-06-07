"""Docker engine prepare steps."""

from __future__ import annotations

from ..plan import PlanStep
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_docker_engine_check(ctx: PrepareContext) -> PlanStep:
    description = "Check Docker engine and running odpm containers"
    if not ctx.config.check_system:
        return make_plan_step(
            "docker.engine.check",
            description,
            "skip",
            False,
            "check_system disabled; Docker check skipped",
        )
    return make_plan_step(
        "docker.engine.check",
        description,
        "run",
        True,
        "verify Docker engine and containers",
    )


def exec_docker_engine_check(ctx: PrepareContext) -> None:
    ctx.system_checker.check_docker()
    ctx.system_checker.check_running_containers()
