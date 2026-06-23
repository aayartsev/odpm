"""Manifest lifecycle hook plan steps for ``odpm plan``."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..extensions.context import ExtensionHostContext
from ..extensions.hooks import LifecyclePhase, parse_hook_phase
from ..plan import PlanStep
from ..prepare.helpers import make_plan_step
from .l10n import plan_msg

if TYPE_CHECKING:
    pass


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


def _evaluate_hook_phase(ext: ExtensionHostContext, phase: LifecyclePhase) -> PlanStep | None:
    shell_commands, plugin_ids = parse_hook_phase(ext.manifest_hooks, phase)
    if not shell_commands and not plugin_ids:
        return None
    description = plan_msg("Run manifest {PHASE} lifecycle hooks", PHASE=phase)
    return make_plan_step(
        f"hooks.{phase}",
        description,
        "run",
        phase != "post_prepare",
        _hook_step_reason(phase, shell_commands, plugin_ids),
    )


def build_manifest_hook_plan_steps(
    ext: ExtensionHostContext,
) -> tuple[PlanStep, ...]:
    """Plan steps for hooks that run outside the prepare-step registry."""
    steps: list[PlanStep] = []
    for phase in cast(tuple[LifecyclePhase, ...], ("post_prepare", "pre_up")):
        step = _evaluate_hook_phase(ext, phase)
        if step is not None:
            steps.append(step)
    return tuple(steps)


def insert_prepare_hook_steps(
    prepare_steps: list[PlanStep],
    hook_steps: tuple[PlanStep, ...],
) -> list[PlanStep]:
    """Append ``hooks.post_prepare`` after built-in/extension prepare steps."""
    post_prepare = next((step for step in hook_steps if step.id == "hooks.post_prepare"), None)
    if post_prepare is None:
        return prepare_steps
    ordered = list(prepare_steps)
    ordered.append(post_prepare)
    return ordered


def insert_runtime_hook_steps(
    runtime_steps: list[PlanStep],
    hook_steps: tuple[PlanStep, ...],
) -> list[PlanStep]:
    pre_up = next((step for step in hook_steps if step.id == "hooks.pre_up"), None)
    if pre_up is None:
        return runtime_steps
    ordered = list(runtime_steps)
    compose_index = next(
        (index for index, step in enumerate(ordered) if step.id == "compose.up"),
        len(ordered),
    )
    ordered.insert(compose_index, pre_up)
    return ordered
