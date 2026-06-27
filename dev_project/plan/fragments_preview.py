"""Per-service compose fragment plan steps."""

from __future__ import annotations

from ..compose.fragments import collect_compose_services, compose_fragments_need_materialize
from ..plan import PlanStep
from ..prepare.helpers import make_plan_step
from ..prepare.types import PrepareContext
from .l10n import plan_msg


def build_compose_fragment_service_plan_steps(
    ctx: PrepareContext,
) -> tuple[PlanStep, ...]:
    services = collect_compose_services(ctx.extension_host())
    odpm_scenario = ctx.host_ctx.user_env.odpm_scenario
    steps: list[PlanStep] = []
    for name in sorted(services):
        single = {name: services[name]}
        description = plan_msg(
            "Materialize compose fragment for service {NAME}", NAME=name
        )
        if compose_fragments_need_materialize(
            ctx.host_ctx.project_dir,
            single,
            odpm_scenario=odpm_scenario,
        ):
            outcome = "update"
            reason = plan_msg("compose fragment {NAME} stale", NAME=name)
        else:
            outcome = "noop"
            reason = plan_msg("compose fragment {NAME} up to date", NAME=name)
        steps.append(
            make_plan_step(
                f"compose.fragment.{name}",
                description,
                outcome,
                True,
                reason,
            )
        )
    return tuple(steps)


def expand_compose_fragment_plan_steps(
    prepare_steps: list[PlanStep],
    ctx: PrepareContext,
) -> list[PlanStep]:
    """Insert per-service fragment steps immediately before ``compose.fragments``."""
    fragment_steps = build_compose_fragment_service_plan_steps(ctx)
    if not fragment_steps:
        return prepare_steps
    ordered = list(prepare_steps)
    insert_at = next(
        (index for index, step in enumerate(ordered) if step.id == "compose.fragments"),
        len(ordered),
    )
    for offset, step in enumerate(fragment_steps):
        ordered.insert(insert_at + offset, step)
    return ordered
