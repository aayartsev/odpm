"""Formatters and JSON serialization for odpm --plan output."""

from __future__ import annotations

import json
from typing import Any

from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..translations import _
from .core import OdpmPlan, PlanStep
from .compose_runtime import compose_up_force_recreate_value
from .step_groups import plan_group_header, plan_group_key_for_step


PLAN_JSON_VERSION = 1


def plan_has_required_changes(plan: OdpmPlan) -> bool:
    return any(step.should_execute() and step.required for step in plan.steps)


def _format_required(step: PlanStep) -> str:
    if step.outcome in ("noop", "skip"):
        return "-"
    return "yes" if step.required else "no"


def compose_up_info_from_plan(
    plan: OdpmPlan, host_ctx: HostProjectContext, args: OdpmCliArgs
) -> dict[str, Any] | None:
    if not any(step.id == "compose.up" for step in plan.steps):
        return None

    return {"force_recreate": compose_up_force_recreate_value(host_ctx, args)}


def plan_step_to_dict(step: PlanStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "outcome": step.outcome,
        "required": step.required,
        "description": step.description,
        "reason": step.reason,
    }


def plan_diff_to_dict(file_diff) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": file_diff.path}
    if file_diff.summary is not None:
        payload["summary"] = file_diff.summary
    if file_diff.unified_diff is not None:
        payload["unified_diff"] = file_diff.unified_diff
    return payload


def plan_to_dict(
    plan: OdpmPlan, host_ctx: HostProjectContext, args: OdpmCliArgs
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "plan_version": PLAN_JSON_VERSION,
        "steps": [plan_step_to_dict(step) for step in plan.steps],
        "warnings": list(plan.warnings),
    }
    compose_up = compose_up_info_from_plan(plan, host_ctx, args)
    if compose_up is not None:
        payload["compose_up"] = compose_up
    if plan.diffs:
        payload["diffs"] = [plan_diff_to_dict(file_diff) for file_diff in plan.diffs]
    return payload


def format_plan_table(plan: OdpmPlan) -> str:
    lines = [
        _("Action   Required  ID                    Reason"),
        "-" * 72,
    ]
    emitted_groups: set[str] = set()
    last_group: str | None = None
    for step in plan.steps:
        group_key = plan_group_key_for_step(step.id)
        if (
            group_key is not None
            and group_key != last_group
            and group_key not in emitted_groups
        ):
            if len(lines) > 2:
                lines.append("")
            lines.append(f"# {plan_group_header(group_key)}")
            emitted_groups.add(group_key)
            last_group = group_key
        elif group_key is not None:
            last_group = group_key
        lines.append(
            f"{step.outcome.upper():<8} {_format_required(step):<8}  "
            f"{step.id:<22} {step.reason}"
        )
    if plan.warnings:
        lines.append("")
        lines.append(_("Warnings:"))
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    if plan.diffs:
        lines.append("")
        lines.append(_("Planned changes:"))
        for file_diff in plan.diffs:
            if file_diff.unified_diff:
                header = file_diff.path
                if file_diff.summary:
                    header = f"{file_diff.path} ({file_diff.summary})"
                lines.append(header)
                lines.extend(file_diff.unified_diff.rstrip("\n").splitlines())
            elif file_diff.summary:
                lines.append(f"{file_diff.path}: {file_diff.summary}")
            else:
                lines.append(file_diff.path)
    return "\n".join(lines)


def format_plan_json(
    plan: OdpmPlan, host_ctx: HostProjectContext, args: OdpmCliArgs
) -> str:
    return json.dumps(
        plan_to_dict(plan, host_ctx, args),
        ensure_ascii=False,
        indent=2,
    )


def resolve_plan_format(args: OdpmCliArgs | None) -> str:
    plan_format = args.plan_format if args is not None else "table"
    if plan_format not in ("table", "json"):
        return "table"
    return plan_format


def format_plan(
    plan: OdpmPlan,
    args: OdpmCliArgs | None = None,
    host_ctx: HostProjectContext | None = None,
) -> str:
    if resolve_plan_format(args) == "json":
        if host_ctx is None:
            raise ValueError("host_ctx is required for JSON plan output")
        return format_plan_json(plan, host_ctx, args or OdpmCliArgs())
    return format_plan_table(plan)
