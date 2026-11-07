"""Ordered launch steps: plan evaluation + post-gate execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..host.ports import RuntimePorts
from ..plan.compose_runtime import compose_up_would_run
from ..plan.core import PlanStep
from ..prepare.runtime import (
    evaluate_runtime_compose_up,
    evaluate_runtime_ensure_base,
)

if TYPE_CHECKING:
    from ..runtime_coordinator import RuntimeCoordinator


@dataclass(frozen=True)
class LaunchStepDef:
    id: str
    evaluate: Callable[[RuntimePorts], PlanStep | None]
    execute: Callable[[RuntimeCoordinator], None]


def _exec_ensure_base(coordinator: RuntimeCoordinator) -> None:
    coordinator.runtime_backend.ensure_base_image()


def _exec_compose_up(coordinator: RuntimeCoordinator) -> None:
    coordinator.runtime_backend.up()


LAUNCH_STEPS: tuple[LaunchStepDef, ...] = (
    LaunchStepDef(
        "runtime.ensure_base",
        evaluate_runtime_ensure_base,
        _exec_ensure_base,
    ),
    LaunchStepDef(
        "compose.up",
        evaluate_runtime_compose_up,
        _exec_compose_up,
    ),
)


def build_launch_plan_steps(runtime: RuntimePorts) -> tuple[PlanStep, ...]:
    steps: list[PlanStep] = []
    for step_def in LAUNCH_STEPS:
        step = step_def.evaluate(runtime)
        if step is not None:
            steps.append(step)
    return tuple(steps)


def execute_launch_steps(
    coordinator: RuntimeCoordinator, *, force: bool = False
) -> None:
    """Run launch registry in order.

    When ``force`` is false (default for ``run_after_prepare``), skip if the
    stack would not start — same gate as plan visibility (``compose_up_would_run``).
    ``start_containers`` passes ``force=True`` so the facade always ensures+up.
    """
    if not force and not compose_up_would_run(
        coordinator.cli_args, coordinator.host_ctx
    ):
        return
    for step_def in LAUNCH_STEPS:
        step_def.execute(coordinator)
