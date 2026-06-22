"""Plan assembly and formatting entrypoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..host.ports import PipelinePorts, ports_from_config
from .core import OdpmPlan

if TYPE_CHECKING:
    from ..config import Config
    from ..project_env import CreateProjectEnvironment


class OdpmPlanner:
    @classmethod
    def build(
        cls,
        ports_or_config: PipelinePorts | Config,
        args: OdpmCliArgs | None = None,
        project_env: CreateProjectEnvironment | None = None,
    ) -> OdpmPlan:
        from ..prepare import build_plan

        from .diff import build_plan_diffs
        from .runtime_preview import clear_runtime_config_preview_cache

        if isinstance(ports_or_config, PipelinePorts):
            ports = ports_or_config
        else:
            ports = ports_from_config(ports_or_config, project_env, args)
        clear_runtime_config_preview_cache(ports.bootstrap.config)
        plan = build_plan(ports, project_env=project_env)
        diffs = build_plan_diffs(
            plan,
            ports.plan.host_ctx,
            ports.plan.args,
            project_env or ports.compose.project_env,
        )
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
    host_ctx: HostProjectContext | None = None,
) -> str:
    from .format import format_plan as format_plan_output

    return format_plan_output(plan, args, host_ctx)
