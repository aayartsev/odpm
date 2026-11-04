"""Whitelist of prepare step ids for ``--stop-after sources`` (ADR-027)."""

from __future__ import annotations

SOURCES_ONLY_STEP_IDS: frozenset[str] = frozenset(
    {
        "git.lock_load",
        "git.ensure_present",
        "git.materialize",
        "sources.materialize",
        "hooks.post_clone",
        "project.map_folders",
        "git.lock_apply",
        "git.checkout",
        "git.lock_collect",
        "git.lock_verify",
        "project.update_links",
    }
)


def is_sources_only_prepare(stop_after: str | None) -> bool:
    from ..host.cli import params as cli_params

    return stop_after == cli_params.STOP_AFTER_SOURCES
