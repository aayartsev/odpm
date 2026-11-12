"""Sources change check plan: layer input blocks → need_* trees (ADR-027)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..config.payload import hash_requirements_bytes
from ..git.worktree import show_blob_at_ref
from ..logging import get_module_logger
from .ensure import _developing_git_sha
from .fingerprint import (
    _lock_sha_map,
    compute_app_fingerprint,
    compute_deps_fingerprint,
    compute_lint_fingerprint,
    compute_platform_fingerprint,
    compute_venv_fingerprint,
    layer_image_ref,
)
from .registry import force_rebuild_requested, image_ref_exists

_logger = get_module_logger(__name__)

_TRUTHY = frozenset({"1", "true", "True", "yes", "YES"})
ODPM_FORCE_FULL_SOURCES = "ODPM_FORCE_FULL_SOURCES"
ODPM_DEVELOPING_GIT_SHA = "ODPM_DEVELOPING_GIT_SHA"


@dataclass(frozen=True)
class SourcePlanResult:
    """Flags for conditional materialize after block analysis."""

    sources_change_check_active: bool
    full_sources: bool
    need_platform_tree: bool
    need_platform_bare: bool
    need_deps_trees: bool
    platform_hit: bool
    venv_hit: bool
    deps_hit: bool | None
    app_hit: bool | None
    lint_hit: bool | None
    reason: str
    fail_soft: bool = False


def force_full_sources_requested() -> bool:
    return os.environ.get(ODPM_FORCE_FULL_SOURCES, "").strip() in _TRUTHY


def developing_git_sha_for_plan(bootstrap: Any) -> str:
    """HEAD of developing, or ``ODPM_DEVELOPING_GIT_SHA`` / ``CI_COMMIT_SHA``."""
    for key in (ODPM_DEVELOPING_GIT_SHA, "CI_COMMIT_SHA"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return _developing_git_sha(bootstrap)


def _secrets_baked() -> bool:
    return os.environ.get("ODPM_BAKE_SECRETS", "").strip() in _TRUTHY


def _presence(ref: str, *, remote: bool) -> bool:
    return image_ref_exists(
        ref,
        remote=remote,
        force=force_rebuild_requested(),
    )


def _platform_pin(config: Any) -> str:
    return str(_lock_sha_map(config).get("platform", "") or "")


def _apply_requirements_hash_from_bare(
    config: Any,
    *,
    mirror: str,
    pin: str,
) -> None:
    link = getattr(config, "odoo_platform_project", None)
    if link is None or not pin or not mirror:
        return
    try:
        blob = show_blob_at_ref(
            link,
            mirror=mirror,
            ref=pin,
            path="requirements.txt",
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft path uses empty/override miss
        _logger.warning(
            "sources change check: git show requirements.txt failed (%s); "
            "venv fingerprint may miss",
            exc,
        )
        return
    config.odoo_requirements_hash_override = hash_requirements_bytes(blob)


def full_sources_result(*, reason: str, fail_soft: bool = False) -> SourcePlanResult:
    return SourcePlanResult(
        sources_change_check_active=False,
        full_sources=True,
        need_platform_tree=True,
        need_platform_bare=False,
        need_deps_trees=True,
        platform_hit=False,
        venv_hit=False,
        deps_hit=None,
        app_hit=None,
        lint_hit=None,
        reason=reason,
        fail_soft=fail_soft,
    )


def analyze_source_plan(
    config: Any,
    *,
    program_dir: str,
    remote: bool,
    ensure_bare: Callable[[], str] | None = None,
) -> SourcePlanResult:
    """Fingerprint + presence → need_* flags. Fail-soft → full sources."""
    if force_full_sources_requested():
        return full_sources_result(reason=f"{ODPM_FORCE_FULL_SOURCES}=1")

    need_bare = True
    mirror = ""
    try:
        if ensure_bare is not None:
            mirror = ensure_bare()
        pin = _platform_pin(config)
        if mirror and pin:
            _apply_requirements_hash_from_bare(config, mirror=mirror, pin=pin)

        platform_fp = compute_platform_fingerprint(config, program_dir=program_dir)
        platform_ref = layer_image_ref(
            config, layer="platform", fingerprint=platform_fp
        )
        platform_hit = _presence(platform_ref, remote=remote)

        venv_fp = compute_venv_fingerprint(
            config, program_dir=program_dir, platform_ref=platform_ref
        )
        venv_ref = layer_image_ref(config, layer="venv", fingerprint=venv_fp)
        venv_hit = _presence(venv_ref, remote=remote)

        deps_fp = compute_deps_fingerprint(
            config, program_dir=program_dir, platform_ref=venv_ref
        )
        if deps_fp is None:
            deps_hit: bool | None = None
            parent_ref = venv_ref
            need_deps = False
        else:
            deps_ref = layer_image_ref(config, layer="deps", fingerprint=deps_fp)
            deps_hit = _presence(deps_ref, remote=remote)
            parent_ref = deps_ref
            need_deps = not deps_hit

        try:
            developing_sha = developing_git_sha_for_plan(config)
            app_fp = compute_app_fingerprint(
                config,
                program_dir=program_dir,
                parent_ref=parent_ref,
                developing_git_sha=developing_sha,
                secrets_baked=_secrets_baked(),
            )
            app_ref = layer_image_ref(config, layer="app", fingerprint=app_fp)
            app_hit: bool | None = _presence(app_ref, remote=remote)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("sources change check: app fingerprint soft-fail: %s", exc)
            app_hit = None

        project = Path(getattr(config, "project_dir", "") or "")
        if (project / ".pre-commit-config.yaml").is_file():
            lint_fp = compute_lint_fingerprint(
                config, program_dir=program_dir, platform_fp=platform_fp
            )
            lint_ref = layer_image_ref(config, layer="lint", fingerprint=lint_fp)
            lint_hit: bool | None = _presence(lint_ref, remote=remote)
        else:
            lint_hit = None

        need_platform_tree = not platform_hit
        return SourcePlanResult(
            sources_change_check_active=True,
            full_sources=False,
            need_platform_tree=need_platform_tree,
            need_platform_bare=need_bare,
            need_deps_trees=need_deps,
            platform_hit=platform_hit,
            venv_hit=venv_hit,
            deps_hit=deps_hit,
            app_hit=app_hit,
            lint_hit=lint_hit,
            reason="sources change check: blocks analyzed",
            fail_soft=False,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft to full materialize
        _logger.warning(
            "sources change check failed (%s); falling back to full materialize",
            exc,
        )
        return full_sources_result(
            reason=f"sources change check failed: {exc}",
            fail_soft=True,
        )


__all__ = [
    "ODPM_FORCE_FULL_SOURCES",
    "SourcePlanResult",
    "analyze_source_plan",
    "developing_git_sha_for_plan",
    "force_full_sources_requested",
    "full_sources_result",
]
