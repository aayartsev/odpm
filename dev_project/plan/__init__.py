"""Dry-run plan for ``odpm plan`` / ``odpm --plan``.

Predicts prepare and runtime steps without running git materialization,
writing runtime config or root compose, or ``docker compose up``. Loading
configuration does not upgrade templates under ``.odpm/`` (normal runs still
sync them). Unless ``--plan-no-docker`` is set, odpm may probe the local
compose stack for ``compose.up`` predictions.
"""

from .core import (
    OdpmPlan,
    PlanStep,
    PlanStepOutcome,
    deps_lock_file_exists,
    dockerfile_template_relative,
    project_template_needs_upgrade,
    runtime_config_stale,
    skip_git_update,
    update_lock_requested,
)
from .planner import OdpmPlanner, format_plan

__all__ = [
    "OdpmPlan",
    "OdpmPlanner",
    "PlanStep",
    "PlanStepOutcome",
    "deps_lock_file_exists",
    "dockerfile_template_relative",
    "format_plan",
    "project_template_needs_upgrade",
    "runtime_config_stale",
    "skip_git_update",
    "update_lock_requested",
]
