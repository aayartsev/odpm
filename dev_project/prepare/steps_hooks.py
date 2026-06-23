"""Manifest lifecycle hook prepare steps."""

from __future__ import annotations

from ..extensions.hooks import LifecyclePhase, parse_hook_phase, run_lifecycle_hooks
from ..plan import PlanStep
from ..plan.l10n import plan_msg
from .helpers import make_plan_step
from .types import PrepareContext


def _hook_step_reason(
    phase: str,
    shell_commands: tuple[tuple[str, ...], ...],
    plugin_ids: tuple[str, ...],
) -> str:
    if not shell_commands and not plugin_ids:
        return plan_msg("no {PHASE} hooks configured", PHASE=phase)
    parts: list[str] = []
    if shell_commands:
        parts.append(
            plan_msg("{COUNT} shell command(s)", COUNT=len(shell_commands))
        )
    if plugin_ids:
        parts.append(
            plan_msg("plugins: {PLUGIN_LIST}", PLUGIN_LIST=", ".join(plugin_ids))
        )
    return "; ".join(parts)


def _evaluate_hook_phase(ctx: PrepareContext, phase: LifecyclePhase) -> PlanStep:
    description = plan_msg("Run manifest {PHASE} lifecycle hooks", PHASE=phase)
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
            plan_msg("no {PHASE} hooks configured", PHASE=phase),
        )
    return make_plan_step(
        f"hooks.{phase}",
        description,
        "run",
        phase == "post_clone",
        _hook_step_reason(phase, shell_commands, plugin_ids),
    )


def evaluate_hooks_post_clone(ctx: PrepareContext) -> PlanStep:
    return _evaluate_hook_phase(ctx, "post_clone")


def exec_hooks_post_clone(ctx: PrepareContext) -> None:
    run_lifecycle_hooks(
        ctx.extension_host(),
        "post_clone",
        cwd=ctx.host_ctx.project_dir,
        env_resolver=ctx.env_resolver,
    )
