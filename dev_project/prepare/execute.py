"""Prepare context construction, plan building, and execution."""

from __future__ import annotations

from ..git.deps_lock_manager import DepsLockManager
from ..errors import PipelineError
from ..host.cli.args import OdpmCliArgs
from ..git.deps_lock import deps_lock_path, load_deps_lock
from ..host.context import HostProjectContext
from ..logging import get_module_logger
from ..plan import OdpmPlan, PlanStep, deps_lock_file_exists
from .helpers import skip_git, update_lock
from .registry import get_prepare_steps
from .runtime import build_runtime_plan_steps, build_runtime_plan_warnings
from ..config import Config
from ..compose.generator import ComposeGenerator
from ..project_env import CreateProjectEnvironment
from ..project_env.links import ProjectLinks
from ..project_env.templates import ProjectTemplates
from ..protocols import SystemCheckerProtocol
from .types import PrepareContext, PrepareStepDef

_logger = get_module_logger(__name__)


class PlanOnlyProjectEnv:
    """Unused placeholder; prepare plan evaluation reads only config and CLI args."""


class PlanOnlySystemChecker:
    """Unused placeholder; prepare plan evaluation reads only config and CLI args."""


def evaluate_prepare_step(step_def: PrepareStepDef, ctx: PrepareContext) -> PlanStep:
    return step_def.evaluate(ctx)


def _resolve_prepare_services(
    project_env: CreateProjectEnvironment,
) -> tuple[ProjectTemplates, ComposeGenerator, ProjectLinks]:
    if isinstance(project_env, CreateProjectEnvironment):
        return (
            project_env.templates,
            project_env.compose_generator,
            project_env.links,
        )
    templates = ProjectTemplates(project_env)
    compose_generator = ComposeGenerator(project_env)
    links = ProjectLinks(project_env)
    return templates, compose_generator, links


def make_prepare_context(
    config: Config,
    project_env: CreateProjectEnvironment,
    system_checker: SystemCheckerProtocol,
    args: OdpmCliArgs,
) -> PrepareContext:
    templates, compose_generator, links = _resolve_prepare_services(project_env)
    return PrepareContext(
        config=config,
        project_env=project_env,
        templates=templates,
        compose_generator=compose_generator,
        links=links,
        system_checker=system_checker,
        args=args,
        host_ctx=HostProjectContext.from_config(config, arguments=args),
    )


def collect_prepare_warnings(ctx: PrepareContext) -> tuple[str, ...]:
    warnings: list[str] = []
    if ctx.host_ctx.update_lock and ctx.host_ctx.skip_git_update:
        warnings.append("--update-lock cannot be used together with --no-git-update")
    if (
        deps_lock_file_exists(ctx.host_ctx.project_dir)
        and not skip_git(ctx)
        and not update_lock(ctx)
    ):
        try:
            load_deps_lock(deps_lock_path(ctx.host_ctx.project_dir))
        except ValueError:
            warnings.append(
                "Invalid .odpm/deps.lock.json; lock verify step omitted from plan"
            )
    from ..plan.secrets_preview import secrets_gitignore_warning

    gitignore_warning = secrets_gitignore_warning(ctx.host_ctx.project_dir)
    if gitignore_warning:
        warnings.append(gitignore_warning)
    from ..plan.database_preview import collect_database_drift_warnings_for_host
    from ..plan.locks_preview import collect_git_lock_warnings

    warnings.extend(
        collect_database_drift_warnings_for_host(ctx.host_ctx, ctx.config)
    )
    warnings.extend(collect_git_lock_warnings(ctx.host_ctx, ctx.manifest_view))
    return tuple(warnings)


def evaluate_prepare_plan(ctx: PrepareContext) -> tuple[PlanStep, ...]:
    return tuple(step_def.evaluate(ctx) for step_def in get_prepare_steps())


def collect_execute_step_ids(ctx: PrepareContext) -> tuple[str, ...]:
    return tuple(
        step.id for step in evaluate_prepare_plan(ctx) if step.should_execute()
    )


def build_prepare_plan(ctx: PrepareContext) -> OdpmPlan:
    return OdpmPlan(
        steps=evaluate_prepare_plan(ctx),
        warnings=collect_prepare_warnings(ctx),
    )


def build_plan(
    config: Config,
    args: OdpmCliArgs,
    project_env: CreateProjectEnvironment | None = None,
) -> OdpmPlan:
    ctx = make_prepare_context(
        config,
        PlanOnlyProjectEnv(),  # type: ignore[arg-type]
        PlanOnlySystemChecker(),  # type: ignore[arg-type]
        args,
    )
    prepare_plan = build_prepare_plan(ctx)
    runtime_steps = build_runtime_plan_steps(
        config, args, ctx.host_ctx, project_env
    )
    runtime_warnings = build_runtime_plan_warnings(config, args, ctx.host_ctx)
    return OdpmPlan(
        steps=prepare_plan.steps + runtime_steps,
        warnings=prepare_plan.warnings + runtime_warnings,
    )


def validate_prepare_context(ctx: PrepareContext) -> None:
    if ctx.host_ctx.update_lock and ctx.host_ctx.skip_git_update:
        message = "--update-lock cannot be used together with --no-git-update"
        _logger.error(message)
        raise PipelineError(message, exit_code=1)


def execute_prepare(ctx: PrepareContext) -> None:
    validate_prepare_context(ctx)
    ctx.lock_manager = DepsLockManager(ctx.config)
    for step_def in get_prepare_steps():
        outcome = step_def.evaluate(ctx)
        if outcome.should_execute():
            step_def.execute(ctx)
    from ..extensions.hooks import run_lifecycle_hooks

    run_lifecycle_hooks(
        ctx.extension_host(),
        "post_prepare",
        cwd=ctx.host_ctx.project_dir,
    )


collect_prepare_step_ids = collect_execute_step_ids
