"""Database drift prepare step (plan preview and interactive resolve)."""

from __future__ import annotations

from ..database.drift import (
    drifts_requiring_resolution,
    has_blocking_database_drift,
    meaningful_database_drifts,
)
from ..database.resolve import resolve_database_drifts
from ..plan import PlanStep
from ..plan.l10n import plan_msg
from .helpers import make_plan_step
from .types import PrepareContext

_STEP_DESCRIPTION = "Check database configuration drift against last_run snapshot"
_MSG_NO_DRIFT = "database configuration matches last_run snapshot"
_MSG_FIRST_RUN = "first database run (no last_run snapshot yet)"


def evaluate_database_drift(ctx: PrepareContext) -> PlanStep:
    _current, drifts = ctx.detect_database_drift()
    meaningful = meaningful_database_drifts(drifts)
    pending = drifts_requiring_resolution(drifts)
    description = plan_msg(_STEP_DESCRIPTION)
    if not meaningful:
        reason = plan_msg(_MSG_FIRST_RUN if drifts else _MSG_NO_DRIFT)
        return make_plan_step(
            "database.drift",
            description,
            "noop",
            False,
            reason,
        )
    kinds = ", ".join(drift.kind for drift in meaningful)
    required = has_blocking_database_drift(pending or meaningful)
    reason = plan_msg(
        "database configuration drift detected: {KINDS}", KINDS=kinds
    )
    outcome = "run" if pending else "noop"
    return make_plan_step(
        "database.drift",
        description,
        outcome,
        required,
        reason,
    )


def exec_database_drift(ctx: PrepareContext) -> None:
    resolve_database_drifts(ctx)
