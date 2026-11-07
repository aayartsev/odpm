"""Plan assembly and formatting entrypoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..host.ports import PipelinePorts
from ..prepare import build_plan
from .core import OdpmPlan
from .diff import build_plan_diffs
from .format import format_plan as format_plan_output
from ..config.assembly import ports_from_assembled
if TYPE_CHECKING:
    from ..project_env import CreateProjectEnvironment


class OdpmPlanner:
    @classmethod
    def build(
        cls,
        ports_or_config: PipelinePorts | Any,
        args: OdpmCliArgs | None = None,
        project_env: CreateProjectEnvironment | None = None,
    ) -> OdpmPlan:
        if isinstance(ports_or_config, PipelinePorts):
            ports = ports_or_config
        else:
            ports = ports_from_assembled(ports_or_config, project_env, args)
        ports.bootstrap.clear_runtime_config_preview_cache()
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
    return format_plan_output(plan, args, host_ctx)
