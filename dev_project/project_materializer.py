"""Orchestrate host-side project file generation (git, templates, compose)."""

from __future__ import annotations

from .host.ports import PipelinePorts
from .plan import OdpmPlan
from .prepare import build_plan, execute_prepare, make_prepare_context
from .protocols import SystemCheckerProtocol


class ProjectMaterializer:
    """Run the prepare-phase side effects for a host project."""

    def run(
        self,
        ports: PipelinePorts,
        system_checker: SystemCheckerProtocol,
        *,
        dry_run: bool = False,
    ) -> OdpmPlan | None:
        if dry_run:
            return build_plan(ports)

        ctx = make_prepare_context(
            ports,
            ports.compose.project_env,
            system_checker,
        )
        execute_prepare(ctx)
        return None
