"""CI sources change check: attach SourcePlanResult on PrepareContext."""

from __future__ import annotations

import os

from ..image_layers.source_plan import (
    SourcePlanResult,
    analyze_source_plan,
    force_full_sources_requested,
    full_sources_result,
)
from ..logging import get_module_logger
from ..project_env.image_build.resolve import resolve_ci_image_push
from ..system_check_policy import environ_from_host_context
from .sources_only import is_image_ensure_prepare, is_sources_only_prepare
from .types import PrepareContext

_logger = get_module_logger(__name__)


def sources_change_check_eligible(ctx: PrepareContext) -> bool:
    """True for scenario ci + sources-only / image-ensure prepare, unless forced full."""
    if force_full_sources_requested():
        return False
    if not ctx.host_ctx.policy.is_ci():
        return False
    args = ctx.args
    stop_after = getattr(args, "stop_after", None)
    return is_sources_only_prepare(stop_after) or is_image_ensure_prepare(args)


def _remote_for_sources_change_check(ctx: PrepareContext) -> bool:
    environ = environ_from_host_context(ctx.host_ctx)
    push = resolve_ci_image_push(ctx.args, environ=environ)
    registry = os.environ.get("ODPM_BASE_IMAGE_REGISTRY") or os.environ.get(
        "CI_REGISTRY_IMAGE", ""
    )
    return bool(push or registry)


def get_or_build_source_plan(ctx: PrepareContext) -> SourcePlanResult:
    """Cache analysis on ctx; ensure platform bare when change-check eligible."""
    cached = getattr(ctx, "source_plan", None)
    if cached is not None:
        return cached

    if not sources_change_check_eligible(ctx):
        if force_full_sources_requested():
            result = full_sources_result(reason="ODPM_FORCE_FULL_SOURCES=1")
        else:
            result = full_sources_result(reason="sources change check not active")
        ctx.source_plan = result
        return result

    bootstrap = ctx.ports.bootstrap
    assembled = getattr(bootstrap, "_assembled", bootstrap)

    def _ensure_bare() -> str:
        return ctx.git_repos.ensure_platform_bare_pin()

    result = analyze_source_plan(
        assembled,
        program_dir=str(ctx.host_ctx.program_dir),
        remote=_remote_for_sources_change_check(ctx),
        ensure_bare=_ensure_bare,
    )
    if result.fail_soft:
        _logger.warning(
            "sources change check fail-soft → full materialize (%s)",
            result.reason,
        )
    ctx.source_plan = result
    return result
