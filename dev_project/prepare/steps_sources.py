"""Prepare step for manifest ``service_sources`` materialize."""

from __future__ import annotations

from ..git.service_sources import (
    apply_materialized_service_sources,
    collect_service_source_paths,
    ensure_service_sources_present,
    materialize_service_sources,
    service_sources_need_materialize_for_view,
)
from ..plan.core import PlanStep
from ..plan.l10n import plan_msg
from ..symlinks.manager import SymlinkManager
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

    odoo_projects_dir = ctx.host_ctx.user_env.odoo_projects_dir
    if skip_git(ctx):
        if service_sources_need_materialize_for_view(
            manifest_view=view,
            odoo_projects_dir=odoo_projects_dir,
        ):
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

    if service_sources_need_materialize_for_view(
        manifest_view=view,
        odoo_projects_dir=odoo_projects_dir,
    ):
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
    view = ctx.manifest_view
    config = ctx.ports.bootstrap.config
    if view is None or not view.service_sources:
        SymlinkManager(config).sync_service_source_project_links({})
        return

    lock_entries: dict = {}
    if ctx.lock_manager is not None:
        lock_entries = ctx.lock_manager.lock_entries_for_service_sources()
    if skip_git(ctx):
        ensure_service_sources_present(config)
        paths = collect_service_source_paths(config)
    else:
        paths = materialize_service_sources(config, lock_entries=lock_entries)
    apply_materialized_service_sources(config, paths)
