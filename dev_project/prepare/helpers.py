"""Shared helpers for prepare step evaluation."""

from __future__ import annotations

from ..git.deps_lock import deps_lock_path, load_deps_lock
from ..plan import PlanStep, PlanStepOutcome, deps_lock_file_exists
from .types import PrepareContext


def skip_git(ctx: PrepareContext) -> bool:
    return ctx.host_ctx.skip_git_update


def update_lock(ctx: PrepareContext) -> bool:
    return ctx.host_ctx.update_lock


def lock_verify_available(ctx: PrepareContext) -> bool:
    if skip_git(ctx) or update_lock(ctx):
        return False
    if not deps_lock_file_exists(ctx.host_ctx.project_dir):
        return False
    try:
        load_deps_lock(deps_lock_path(ctx.host_ctx.project_dir))
    except ValueError:
        return False
    return True


def make_plan_step(
    step_id: str,
    description: str,
    outcome: PlanStepOutcome,
    required: bool,
    reason: str,
) -> PlanStep:
    return PlanStep(step_id, description, outcome, required, reason)
