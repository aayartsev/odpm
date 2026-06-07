"""Docker engine prepare steps."""

from __future__ import annotations

from ..plan import PlanStep
from ..system_check_policy import SystemCheckPolicy
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_docker_engine_check(ctx: PrepareContext) -> PlanStep:
    description = "Check Docker engine"
    policy = SystemCheckPolicy.from_config(ctx.config)
    if not policy.beginner_docker:
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
        "verify Docker engine",
    )


def exec_docker_engine_check(ctx: PrepareContext) -> None:
    ctx.system_checker.check_docker()


def evaluate_docker_ports_release(ctx: PrepareContext) -> PlanStep:
    description = "Stop containers occupying odpm ports"
    policy = SystemCheckPolicy.from_config(ctx.config)
    if not policy.developer_port_release:
        return make_plan_step(
            "docker.ports.release",
            description,
            "skip",
            False,
            "port release runs only in developer scenario",
        )
    return make_plan_step(
        "docker.ports.release",
        description,
        "run",
        False,
        "free odoo, debugger, postgres, and gevent ports before compose up",
    )


def exec_docker_ports_release(ctx: PrepareContext) -> None:
    ctx.system_checker.check_running_containers()
