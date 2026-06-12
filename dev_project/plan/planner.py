"""Plan assembly and formatting entrypoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..host.cli.args import OdpmCliArgs
from .core import OdpmPlan

if TYPE_CHECKING:
    from ..config import Config
    from ..project_env import CreateProjectEnvironment


class OdpmPlanner:
    @classmethod
    def build(
        cls,
        config: Config,
        args: OdpmCliArgs,
        project_env: CreateProjectEnvironment | None = None,
    ) -> OdpmPlan:
        from ..prepare import build_plan

        from .diff import build_plan_diffs
        from .runtime_preview import clear_runtime_config_preview_cache

        clear_runtime_config_preview_cache(config)
        plan = build_plan(config, args, project_env)
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
    config: Config | None = None,
) -> str:
    from .format import format_plan as format_plan_output

    return format_plan_output(plan, args, config)
