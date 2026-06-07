"""Dry-run plan for ``odpm plan`` / ``odpm --plan``.

Predicts prepare and runtime steps without running git materialization,
writing runtime config or root compose, or ``docker compose up``. Loading
configuration does not upgrade templates under ``.odpm/`` (normal runs still
sync them). Unless ``--plan-no-docker`` is set, odpm may probe the local
compose stack for ``compose.up`` predictions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from . import constants
from .config.payload import runtime_config_path
from .host_cli.args import OdpmCliArgs
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


def skip_git_update(arguments: OdpmCliArgs) -> bool:
    return bool(arguments.no_git_update)


def update_lock_requested(arguments: OdpmCliArgs) -> bool:
    return bool(arguments.update_lock)


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
        args: OdpmCliArgs,
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


def format_plan(
    plan: OdpmPlan,
    args: OdpmCliArgs | None = None,
    config: "Config | None" = None,
) -> str:
    from .plan_format import format_plan as format_plan_output

    return format_plan_output(plan, args, config)
