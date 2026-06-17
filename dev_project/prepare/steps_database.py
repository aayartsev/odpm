"""Database drift prepare step (plan preview; resolve in a later phase)."""

from __future__ import annotations

from ..database.drift import (
    detect_database_drift_for_config,
    has_blocking_database_drift,
    meaningful_database_drifts,
)
from ..plan import PlanStep
from ..translations import _
from .helpers import make_plan_step
from .types import PrepareContext

_STEP_DESCRIPTION = _("Check database configuration drift against last_run snapshot")
_MSG_NO_DRIFT = _("database configuration matches last_run snapshot")
_MSG_FIRST_RUN = _("first database run (no last_run snapshot yet)")


def evaluate_database_drift(ctx: PrepareContext) -> PlanStep:
    _current, drifts = detect_database_drift_for_config(ctx.config)
    meaningful = meaningful_database_drifts(drifts)
    if not meaningful:
        reason = _MSG_FIRST_RUN if drifts else _MSG_NO_DRIFT
        return make_plan_step(
            "database.drift",
            _STEP_DESCRIPTION,
            "noop",
            False,
            reason,
        )
    kinds = ", ".join(drift.kind for drift in meaningful)
    required = has_blocking_database_drift(meaningful)
    reason = _("database configuration drift detected: {KINDS}").format(KINDS=kinds)
    return make_plan_step(
        "database.drift",
        _STEP_DESCRIPTION,
        "run",
        required,
        reason,
    )


def exec_database_drift(_ctx: PrepareContext) -> None:
    """Drift resolution is implemented in a later phase."""
