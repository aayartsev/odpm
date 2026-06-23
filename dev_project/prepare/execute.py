"""Prepare context construction, plan building, and execution."""

from __future__ import annotations

from ..git.deps_lock import deps_lock_path, load_deps_lock
from ..errors import PipelineError
from ..host.cli.args import OdpmCliArgs
from ..host.ports import PipelinePorts, ports_from_config
from ..logging import get_module_logger
from ..translations import _
from ..plan import OdpmPlan, PlanStep, deps_lock_file_exists
from ..plan.l10n import plan_msg
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
    ports_or_config: PipelinePorts | Config,
    project_env: CreateProjectEnvironment,
    system_checker: SystemCheckerProtocol,
    args: OdpmCliArgs | None = None,
) -> PrepareContext:
    if isinstance(ports_or_config, PipelinePorts):
        ports = ports_or_config
        resolved_args = ports.plan.args
    else:
        resolved_args = args if args is not None else ports_or_config.arguments
        ports = ports_from_config(ports_or_config, project_env, resolved_args)
    templates, compose_generator, links = _resolve_prepare_services(project_env)
    return PrepareContext(
        ports=ports,
        project_env=project_env,
        templates=templates,
        compose_generator=compose_generator,
        links=links,
        system_checker=system_checker,
        args=resolved_args,
        host_ctx=ports.plan.host_ctx,
    )


def _manifest_schema_v2(manifest_view) -> bool:
    from .. import constants

    return (
        manifest_view is not None
        and manifest_view.manifest_schema == constants.MANIFEST_SCHEMA_V2
    )


def collect_prepare_warnings(ctx: PrepareContext) -> tuple[str, ...]:
    warnings: list[str] = []
    if ctx.host_ctx.update_lock and ctx.host_ctx.skip_git_update:
        warnings.append(
            plan_msg("--update-lock cannot be used together with --no-git-update")
        )
    if ctx.host_ctx.sync_manifest_locks and not ctx.host_ctx.update_lock:
        warnings.append(plan_msg("--sync-manifest-locks requires --update-lock"))
    elif (
        ctx.host_ctx.sync_manifest_locks
        and ctx.host_ctx.update_lock
        and not ctx.host_ctx.policy.is_developer()
    ):
        warnings.append(
            plan_msg("--sync-manifest-locks is only supported in developer scenario")
        )
    elif (
        ctx.host_ctx.update_lock
        and ctx.host_ctx.policy.is_developer()
        and not ctx.host_ctx.sync_manifest_locks
        and _manifest_schema_v2(ctx.manifest_view)
    ):
        warnings.append(
            plan_msg(
                "deps.lock will be updated; manifest locks.git unchanged "
                "(use --sync-manifest-locks with --update-lock)"
            )
        )
    if (
        deps_lock_file_exists(ctx.host_ctx.project_dir)
        and not skip_git(ctx)
        and not update_lock(ctx)
    ):
        try:
            load_deps_lock(deps_lock_path(ctx.host_ctx.project_dir))
        except ValueError:
            warnings.append(
                plan_msg(
                    "Invalid .odpm/deps.lock.json; lock verify step omitted from plan"
                )
            )
    from ..plan.secrets_preview import secrets_gitignore_warning

    gitignore_warning = secrets_gitignore_warning(ctx.host_ctx.project_dir)
    if gitignore_warning:
        warnings.append(plan_msg(gitignore_warning))
    from ..plan.database_preview import collect_database_drift_warnings_for_host
    from ..plan.locks_preview import collect_git_lock_warnings

    warnings.extend(
        collect_database_drift_warnings_for_host(
            ctx.host_ctx, ctx.ports.bootstrap
        )
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
    from ..extensions.registry import ensure_project_extensions_loaded
    from ..plan.fragments_preview import expand_compose_fragment_plan_steps
    from ..plan.patches_preview import expand_compose_patch_plan_steps
    from ..plan.hooks_preview import (
        build_manifest_hook_plan_steps,
        insert_prepare_hook_steps,
    )

    manifest_view = ctx.manifest_view
    ensure_project_extensions_loaded(
        ctx.host_ctx.project_dir,
        manifest_extensions=(
            manifest_view.extensions if manifest_view is not None else None
        ),
    )
    steps = list(evaluate_prepare_plan(ctx))
    steps = expand_compose_fragment_plan_steps(steps, ctx)
    steps = expand_compose_patch_plan_steps(steps, ctx)
    hook_steps = build_manifest_hook_plan_steps(ctx.extension_host())
    steps = insert_prepare_hook_steps(steps, hook_steps)
    return OdpmPlan(
        steps=tuple(steps),
        warnings=collect_prepare_warnings(ctx),
    )


def build_plan(
    ports_or_config: PipelinePorts | Config,
    args: OdpmCliArgs | None = None,
    project_env: CreateProjectEnvironment | None = None,
) -> OdpmPlan:
    if isinstance(ports_or_config, PipelinePorts):
        ports = ports_or_config
        prepare_env = (
            ports.compose.project_env
            if project_env is not None
            else PlanOnlyProjectEnv()  # type: ignore[arg-type]
        )
    else:
        config = ports_or_config
        resolved_args = args if args is not None else config.arguments
        ports = ports_from_config(
            config,
            project_env or CreateProjectEnvironment(config),
            resolved_args,
        )
        prepare_env = PlanOnlyProjectEnv()  # type: ignore[arg-type]
    ctx = make_prepare_context(
        ports,
        prepare_env,
        PlanOnlySystemChecker(),  # type: ignore[arg-type]
    )
    prepare_plan = build_prepare_plan(ctx)
    from ..plan.hooks_preview import (
        build_manifest_hook_plan_steps,
        insert_runtime_hook_steps,
    )

    hook_steps = build_manifest_hook_plan_steps(ctx.extension_host())
    runtime_steps = list(build_runtime_plan_steps(ports.runtime, project_env))
    runtime_steps = insert_runtime_hook_steps(runtime_steps, hook_steps)
    runtime_warnings = build_runtime_plan_warnings(ports.runtime)
    return OdpmPlan(
        steps=prepare_plan.steps + tuple(runtime_steps),
        warnings=prepare_plan.warnings + runtime_warnings,
    )


def validate_prepare_context(ctx: PrepareContext) -> None:
    if ctx.host_ctx.update_lock and ctx.host_ctx.skip_git_update:
        message = _("--update-lock cannot be used together with --no-git-update")
        _logger.error(message)
        raise PipelineError(message, exit_code=1)
    if ctx.host_ctx.sync_manifest_locks and not ctx.host_ctx.update_lock:
        message = _("--sync-manifest-locks requires --update-lock")
        _logger.error(message)
        raise PipelineError(message, exit_code=1)


def execute_prepare(ctx: PrepareContext) -> None:
    from ..extensions.registry import ensure_project_extensions_loaded

    validate_prepare_context(ctx)
    manifest_view = ctx.manifest_view
    ensure_project_extensions_loaded(
        ctx.host_ctx.project_dir,
        manifest_extensions=(
            manifest_view.extensions if manifest_view is not None else None
        ),
    )
    ctx.lock_manager = ctx.ports.bootstrap.new_lock_manager()
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
