"""Project layout prepare steps."""

from __future__ import annotations

from ..plan import PlanStep
from ..plan.l10n import plan_msg
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_map_folders(ctx: PrepareContext) -> PlanStep:
    return make_plan_step(
        "project.map_folders",
        plan_msg("Build docker volume mapping for Odoo, venv, and addons"),
        "run",
        True,
        plan_msg("refresh docker volume mapping"),
    )


def evaluate_update_links(ctx: PrepareContext) -> PlanStep:
    return make_plan_step(
        "project.update_links",
        plan_msg("Refresh project symlinks for local codebase access"),
        "run",
        True,
        plan_msg("refresh project symlinks"),
    )


def exec_map_folders(ctx: PrepareContext) -> None:
    ctx.links.map_folders()


def exec_update_links(ctx: PrepareContext) -> None:
    ctx.links.update_links()
