"""Whitelist of prepare step ids for ``--stop-after sources`` (ADR-027)."""

from __future__ import annotations

SOURCES_ONLY_STEP_IDS: frozenset[str] = frozenset(
    {
        "git.lock_load",
        "git.ensure_present",
        "git.materialize_developing",
        "git.materialize_platform",
        "sources.materialize",
        "hooks.post_clone",
        "git.materialize_dependencies",
        "project.map_folders",
        "git.lock_apply",
        "git.checkout",
        "git.lock_collect",
        "git.lock_verify",
        "project.update_links",
    }
)

# ``odpm image … ensure`` needs sources + secrets for optional app bake, and
# root Dockerfile/.dockerignore sync so kaniko/docker build see upgraded
# ``.odpm`` templates (ADR-007). Still skip compose / odoo.conf / docker checks.
IMAGE_ENSURE_STEP_IDS: frozenset[str] = SOURCES_ONLY_STEP_IDS | frozenset(
    {
        "secrets.fetch",
        "secrets.materialize",
        "template.dockerfile",
        "template.dockerignore",
    }
)


def is_sources_only_prepare(stop_after: str | None) -> bool:
    from ..host.cli import params as cli_params

    return stop_after == cli_params.STOP_AFTER_SOURCES


def is_image_ensure_prepare(arguments) -> bool:
    """True when prepare runs under ``odpm image`` without an explicit stop-after."""
    from ..host.cli import params as cli_params

    if getattr(arguments, "stop_after", None):
        return False
    return getattr(arguments, "command", None) == cli_params.IMAGE_SUBCOMMAND
