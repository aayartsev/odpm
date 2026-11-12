"""Project layout prepare steps."""

from __future__ import annotations

from ..plan.core import PlanStep
from ..plan.l10n import plan_msg
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_map_folders(ctx: PrepareContext) -> PlanStep:
    description = plan_msg(
        "Build docker volume mapping for Odoo, venv, and addons "
        "(no dependency clone or OCA discovery)"
    )
    reason = plan_msg("refresh docker volume mapping")
    plan = getattr(ctx, "source_plan", None)
    if plan is not None and plan.sources_change_check_active and not plan.need_platform_tree:
        reason = plan_msg(
            "sources change check: refresh volume mapping without requiring Odoo tree"
        )
    return make_plan_step(
        "project.map_folders",
        description,
        "run",
        True,
        reason,
    )


def evaluate_update_links(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Refresh project symlinks for local codebase access")
    reason = plan_msg("refresh project symlinks")
    plan = getattr(ctx, "source_plan", None)
    if plan is not None and plan.sources_change_check_active and not plan.need_platform_tree:
        reason = plan_msg(
            "sources change check: refresh project links; skip Odoo addons links without tree"
        )
    return make_plan_step(
        "project.update_links",
        description,
        "run",
        True,
        reason,
    )


def exec_map_folders(ctx: PrepareContext) -> None:
    ctx.links.map_folders()


def exec_update_links(ctx: PrepareContext) -> None:
    ctx.links.update_links()
