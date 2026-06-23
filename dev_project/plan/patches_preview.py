"""Manifest compose service patch plan steps."""

from __future__ import annotations

from ..compose.fragments import collect_service_patches
from ..plan import PlanStep
from ..prepare.helpers import make_plan_step
from ..prepare.types import PrepareContext
from .l10n import plan_msg


def build_compose_patch_plan_steps(ctx: PrepareContext) -> tuple[PlanStep, ...]:
    patches = collect_service_patches(ctx.extension_host())
    if not patches:
        return ()
    steps: list[PlanStep] = []
    for name in sorted(patches):
        keys = ", ".join(sorted(patches[name].keys()))
        steps.append(
            make_plan_step(
                f"compose.patch.{name}",
                plan_msg(
                    "Apply manifest compose patch to service {NAME}",
                    NAME=name,
                ),
                "run",
                True,
                plan_msg("patch keys: {KEYS}", KEYS=keys),
            )
        )
    return tuple(steps)


def expand_compose_patch_plan_steps(
    prepare_steps: list[PlanStep],
    ctx: PrepareContext,
) -> list[PlanStep]:
    """Insert per-service patch steps immediately before ``compose.service``."""
    patch_steps = build_compose_patch_plan_steps(ctx)
    if not patch_steps:
        return prepare_steps
    ordered = list(prepare_steps)
    insert_at = next(
        (index for index, step in enumerate(ordered) if step.id == "compose.service"),
        len(ordered),
    )
    for offset, step in enumerate(patch_steps):
        ordered.insert(insert_at + offset, step)
    return ordered
