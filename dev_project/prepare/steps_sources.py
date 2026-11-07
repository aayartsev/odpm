"""Prepare step for manifest ``service_sources`` materialize."""

from __future__ import annotations

from ..plan.core import PlanStep
from ..plan.l10n import plan_msg
from .helpers import make_plan_step, skip_git
from .types import PrepareContext


def evaluate_sources_materialize(ctx: PrepareContext) -> PlanStep:
    description = plan_msg(
        "Clone or update manifest service_sources git repositories"
    )
    view = ctx.manifest_view
    if view is None or not view.service_sources:
        return make_plan_step(
            "sources.materialize",
            description,
            "run",
            True,
            plan_msg("sync project service-sources links"),
        )

    need = ctx.service_sources_need_materialize()
    if skip_git(ctx):
        if need:
            return make_plan_step(
                "sources.materialize",
                description,
                "run",
                True,
                plan_msg("verify service_sources paths exist"),
            )
        return make_plan_step(
            "sources.materialize",
            description,
            "run",
            True,
            plan_msg("inject service_sources paths into env resolver"),
        )

    if need:
        return make_plan_step(
            "sources.materialize",
            description,
            "update",
            True,
            plan_msg("service_sources stale or missing"),
        )
    return make_plan_step(
        "sources.materialize",
        description,
        "run",
        True,
        plan_msg("inject service_sources paths into env resolver"),
    )


def exec_sources_materialize(ctx: PrepareContext) -> None:
    lock_entries: dict = {}
    if ctx.lock_manager is not None:
        lock_entries = ctx.lock_manager.lock_entries_for_service_sources()
    ctx.run_service_sources_materialize(
        skip_git=skip_git(ctx),
        lock_entries=lock_entries,
    )
