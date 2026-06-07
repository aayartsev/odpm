"""Project layout prepare steps."""

from __future__ import annotations

from ..plan import PlanStep
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_map_folders(ctx: PrepareContext) -> PlanStep:
    return make_plan_step(
        "project.map_folders",
        "Build docker volume mapping for Odoo, venv, and addons",
        "run",
        True,
        "refresh docker volume mapping",
    )


def evaluate_update_links(ctx: PrepareContext) -> PlanStep:
    return make_plan_step(
        "project.update_links",
        "Refresh project symlinks for local codebase access",
        "run",
        True,
        "refresh project symlinks",
    )


def exec_map_folders(ctx: PrepareContext) -> None:
    ctx.project_env.map_folders()
