"""Dry-run plan for ``odpm plan`` / ``odpm --plan``.

Predicts prepare and runtime steps without running git materialization,
writing runtime config or root compose, or ``docker compose up``. Loading
configuration does not upgrade templates under ``.odpm/`` (normal runs still
sync them). Unless ``--plan-no-docker`` is set, odpm may probe the local
compose stack for ``compose.up`` predictions.

Leaf types live in :mod:`dev_project.plan.core`. ``OdpmPlanner`` / ``format_plan``
are loaded lazily so ``prepare`` can import ``plan.core`` without a cycle.
"""

from __future__ import annotations

from typing import Any

from .core import (
    OdpmPlan,
    PlanStep,
    PlanStepOutcome,
    deps_lock_file_exists,
    dockerfile_template_relative,
    dockerfile_template_relative_host,
    project_template_needs_upgrade,
    runtime_config_stale,
    skip_git_update,
    update_lock_requested,
)

__all__ = [
    "OdpmPlan",
    "OdpmPlanner",
    "PlanStep",
    "PlanStepOutcome",
    "deps_lock_file_exists",
    "dockerfile_template_relative",
    "dockerfile_template_relative_host",
    "format_plan",
    "project_template_needs_upgrade",
    "runtime_config_stale",
    "skip_git_update",
    "update_lock_requested",
]


def __getattr__(name: str) -> Any:
    if name == "OdpmPlanner":
        from .planner import OdpmPlanner  # noqa: PLC0415  # cycle

        return OdpmPlanner
    if name == "format_plan":
        from .planner import format_plan  # noqa: PLC0415  # cycle

        return format_plan
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
