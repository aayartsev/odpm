"""Dry-run plan for ``odpm --plan``: predict prepare/runtime steps without side effects."""

from __future__ import annotations

import json
import os
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from . import constants
from .config.payload import runtime_config_path
from .host_context import HostProjectContext
from .project_dir_manager import template_needs_upgrade
from .project_env.base_image_identity import base_image_identity_matches

if TYPE_CHECKING:
    from .config import Config
    from .plan_diff import PlanFileDiff
    from .project_env import CreateProjectEnvironment

PlanStepOutcome = Literal["run", "update", "noop", "skip"]


@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    outcome: PlanStepOutcome
    required: bool
    reason: str

    @property
    def action(self) -> str:
        """Backward-compatible alias for the step description."""
        return self.description

    def should_execute(self) -> bool:
        return self.outcome in ("run", "update")


@dataclass(frozen=True)
class OdpmPlan:
    steps: tuple[PlanStep, ...]
    warnings: tuple[str, ...] = ()
    diffs: tuple["PlanFileDiff", ...] = ()


def skip_git_update(arguments: Namespace) -> bool:
    return bool(getattr(arguments, "no_git_update", False))


def update_lock_requested(arguments: Namespace) -> bool:
    return bool(getattr(arguments, "update_lock", False))


def deps_lock_file_exists(project_dir: str) -> bool:
    from .git.deps_lock import deps_lock_path

    return os.path.isfile(deps_lock_path(project_dir))


def project_template_needs_upgrade(
    project_dir: str, relative_path: str, markers: list[str]
) -> bool:
    path = os.path.join(project_dir, relative_path)
    if not os.path.exists(path):
        return True
    return template_needs_upgrade(path, markers)


def runtime_config_stale(config: Config) -> bool:
    path = runtime_config_path(config.project_dir)
    if not os.path.isfile(path):
        return True
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return True
    return payload.get("venv_lock_hash") != config.compute_venv_lock_hash()


def dockerfile_template_relative(config: Config) -> str:
    return os.path.join(
        constants.PROJECT_SERVICE_DIRECTORY,
        config.dockerfile_template_name,
    )


class OdpmPlanner:
    @classmethod
    def build(
        cls,
        config: Config,
        args: Namespace,
        project_env: CreateProjectEnvironment | None = None,
    ) -> OdpmPlan:
        from .plan_diff import build_plan_diffs
        from .plan_runtime_preview import clear_runtime_config_preview_cache
        from .prepare_registry import build_plan

        clear_runtime_config_preview_cache(config)
        plan = build_plan(config, args)
        diffs = build_plan_diffs(plan, config, args, project_env)
        if not diffs:
            return plan
        return OdpmPlan(
            steps=plan.steps,
            warnings=plan.warnings,
            diffs=diffs,
        )


def _format_required(step: PlanStep) -> str:
    if step.outcome in ("noop", "skip"):
        return "-"
    return "yes" if step.required else "no"


def format_plan(plan: OdpmPlan) -> str:
    lines = ["Action   Required  ID                    Reason", "-" * 72]
    for step in plan.steps:
        lines.append(
            f"{step.outcome.upper():<8} {_format_required(step):<8}  "
            f"{step.id:<22} {step.reason}"
        )
    if plan.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    if plan.diffs:
        lines.append("")
        lines.append("Planned changes:")
        for file_diff in plan.diffs:
            if file_diff.unified_diff:
                header = file_diff.path
                if file_diff.summary:
                    header = f"{header} ({file_diff.summary})"
                lines.append(header)
                lines.extend(file_diff.unified_diff.rstrip("\n").splitlines())
            elif file_diff.summary:
                lines.append(f"{file_diff.path}: {file_diff.summary}")
            else:
                lines.append(file_diff.path)
    return "\n".join(lines)
