"""Manifest lifecycle hook prepare steps."""

from __future__ import annotations

from ..extensions.hooks import LifecyclePhase, parse_hook_phase, run_lifecycle_hooks
from ..plan import PlanStep
from .helpers import make_plan_step
from .types import PrepareContext


def _evaluate_hook_phase(ctx: PrepareContext, phase: LifecyclePhase) -> PlanStep:
    description = f"Run manifest {phase} lifecycle hooks"
    shell_commands, plugin_ids = parse_hook_phase(
        ctx.extension_host().manifest_hooks,
        phase,
    )
    if not shell_commands and not plugin_ids:
        return make_plan_step(
            f"hooks.{phase}",
            description,
            "skip",
            False,
            f"no {phase} hooks configured",
        )
    reason_parts: list[str] = []
    if shell_commands:
        reason_parts.append(f"{len(shell_commands)} shell command(s)")
    if plugin_ids:
        reason_parts.append(f"plugins: {', '.join(plugin_ids)}")
    return make_plan_step(
        f"hooks.{phase}",
        description,
        "run",
        phase == "post_clone",
        "; ".join(reason_parts),
    )


def evaluate_hooks_post_clone(ctx: PrepareContext) -> PlanStep:
    return _evaluate_hook_phase(ctx, "post_clone")


def exec_hooks_post_clone(ctx: PrepareContext) -> None:
    run_lifecycle_hooks(
        ctx.extension_host(),
        "post_clone",
        cwd=ctx.host_ctx.project_dir,
    )
