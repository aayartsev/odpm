"""Secrets materialize prepare step."""

from __future__ import annotations

from ..plan import PlanStep
from ..plan.secrets_preview import secrets_needs_update
from ..project_env.secrets import materialize_secrets
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_secrets_materialize(ctx: PrepareContext) -> PlanStep:
    description = "Materialize .odpm/runtime/secrets.json from .odpm/secrets.json"
    if not ctx.host_ctx.policy.mount_runtime_secrets_from_host():
        return make_plan_step(
            "secrets.materialize",
            description,
            "skip",
            True,
            "secrets mount disabled for CI scenario",
        )
    needs_update, reason = secrets_needs_update(ctx.host_ctx.project_dir)
    if needs_update:
        return make_plan_step(
            "secrets.materialize",
            description,
            "update",
            True,
            reason,
        )
    return make_plan_step(
        "secrets.materialize",
        description,
        "noop",
        True,
        reason,
    )


def exec_secrets_materialize(ctx: PrepareContext) -> None:
    if not ctx.host_ctx.policy.mount_runtime_secrets_from_host():
        return
    materialize_secrets(ctx.host_ctx.project_dir)
