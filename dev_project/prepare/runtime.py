"""Runtime-phase plan steps (after prepare)."""

from __future__ import annotations

from argparse import Namespace

from ..host_context import HostProjectContext
from ..plan import PlanStep
from ..plan_compose_preview import vscode_settings_up_to_date
from ..config import Config
from .helpers import make_plan_step


def evaluate_runtime_ci_build_image(
    config: Config, args: Namespace
) -> PlanStep | None:
    if not getattr(args, "build_image", False):
        return None
    return make_plan_step(
        "ci.build_image",
        "Build CI Docker image from prepared context",
        "run",
        True,
        "build CI image from prepared context",
    )


def evaluate_runtime_vscode_settings(config: Config) -> PlanStep | None:
    if config.policy.skip_vscode:
        return None
    description = "Update VS Code launch and workspace settings"
    if vscode_settings_up_to_date(config):
        return make_plan_step(
            "vscode.settings",
            description,
            "noop",
            False,
            "VS Code settings already present",
        )
    return make_plan_step(
        "vscode.settings",
        description,
        "run",
        False,
        "refresh VS Code launch and settings",
    )


def _compose_runtime():
    from .. import prepare_registry

    return prepare_registry


def evaluate_runtime_compose_up(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> PlanStep | None:
    runtime = _compose_runtime()
    if not runtime.compose_up_would_run(args, host_ctx):
        return None
    description = "Run docker compose up"
    reason, _extra_warnings = runtime.evaluate_compose_up_plan(config, args)
    return make_plan_step(
        "compose.up",
        description,
        "run",
        True,
        reason,
    )


def build_runtime_plan_steps(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> tuple[PlanStep, ...]:
    steps: list[PlanStep] = []
    for evaluator in (
        lambda: evaluate_runtime_ci_build_image(config, args),
        lambda: evaluate_runtime_vscode_settings(config),
        lambda: evaluate_runtime_compose_up(config, args, host_ctx),
    ):
        step = evaluator()
        if step is not None:
            steps.append(step)
    return tuple(steps)


def build_runtime_plan_warnings(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> tuple[str, ...]:
    runtime = _compose_runtime()
    if not runtime.compose_up_would_run(args, host_ctx):
        return ()
    _reason, extra_warnings = runtime.evaluate_compose_up_plan(config, args)
    return extra_warnings
