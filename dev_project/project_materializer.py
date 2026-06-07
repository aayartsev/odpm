"""Orchestrate host-side project file generation (git, templates, compose)."""

from __future__ import annotations

from .config import Config
from .host.cli.args import OdpmCliArgs
from .plan import OdpmPlan
from .prepare_registry import build_plan, execute_prepare, make_prepare_context
from .protocols import SystemCheckerProtocol
from .project_env import CreateProjectEnvironment


class ProjectMaterializer:
    """Run the prepare-phase side effects for a host project."""

    def run(
        self,
        config: Config,
        project_env: CreateProjectEnvironment,
        system_checker: SystemCheckerProtocol,
        args: OdpmCliArgs,
        *,
        dry_run: bool = False,
    ) -> OdpmPlan | None:
        if dry_run:
            return build_plan(config, args)

        ctx = make_prepare_context(config, project_env, system_checker, args)
        execute_prepare(ctx)
        return None
