"""Single ordered registry of prepare-phase steps shared by plan and materializer."""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import constants
from .compose_service_builder import ComposeServiceBuilder
from .errors import PipelineError
from .git.deps_lock import deps_lock_path, load_deps_lock
from .git.deps_lock_manager import DepsLockManager
from .host_context import HostProjectContext
from .logging import get_module_logger
from .plan import (
    OdpmPlan,
    PlanStep,
    PlanStepOutcome,
    deps_lock_file_exists,
    dockerfile_template_relative,
    project_template_needs_upgrade,
    runtime_config_stale,
)
from .plan_compose_preview import (
    compose_generate_needs_execute,
    compose_service_needs_update,
    vscode_settings_up_to_date,
)
from .plan_compose_runtime import (
    compose_up_would_run,
    evaluate_compose_up_plan,
)
from .project_env.base_image_identity import base_image_identity_matches

if TYPE_CHECKING:
    from .config import Config
    from .project_env import CreateProjectEnvironment
    from .protocols import SystemCheckerProtocol

_logger = get_module_logger(__name__)


@dataclass
class PrepareContext:
    config: Config
    project_env: CreateProjectEnvironment
    system_checker: SystemCheckerProtocol
    args: Namespace
    host_ctx: HostProjectContext
    lock_manager: DepsLockManager | None = None


@dataclass(frozen=True)
class PrepareStepDef:
    id: str
    description: str
    evaluate: Callable[[PrepareContext], PlanStep]
    execute: Callable[[PrepareContext], None]


def _skip_git(ctx: PrepareContext) -> bool:
    return ctx.host_ctx.skip_git_update


def _update_lock(ctx: PrepareContext) -> bool:
    return ctx.host_ctx.update_lock


def _lock_verify_available(ctx: PrepareContext) -> bool:
    if _skip_git(ctx) or _update_lock(ctx):
        return False
    if not deps_lock_file_exists(ctx.config.project_dir):
        return False
    try:
        load_deps_lock(deps_lock_path(ctx.config.project_dir))
    except ValueError:
        return False
    return True


def _step(
    step_id: str,
    description: str,
    outcome: PlanStepOutcome,
    required: bool,
    reason: str,
) -> PlanStep:
    return PlanStep(step_id, description, outcome, required, reason)


def _evaluate_git_lock_load(ctx: PrepareContext) -> PlanStep:
    description = "Load .odpm/deps.lock.json and enter apply mode before checkout"
    if _skip_git(ctx):
        return _step(
            "git.lock_load",
            description,
            "skip",
            False,
            "skipped with --no-git-update",
        )
    if _update_lock(ctx):
        return _step(
            "git.lock_load",
            description,
            "skip",
            False,
            "skipped with --update-lock",
        )
    return _step(
        "git.lock_load",
        description,
        "run",
        True,
        "load deps.lock before checkout",
    )


def _evaluate_git_ensure_present(ctx: PrepareContext) -> PlanStep:
    description = "Verify local platform and developing git directories exist"
    if not _skip_git(ctx):
        return _step(
            "git.ensure_present",
            description,
            "skip",
            False,
            "git repos will be materialized",
        )
    return _step(
        "git.ensure_present",
        description,
        "run",
        True,
        "verify local git directories exist",
    )


def _evaluate_git_materialize(ctx: PrepareContext) -> PlanStep:
    description = "Clone or update platform, developing, and dependency git repos"
    if _skip_git(ctx):
        return _step(
            "git.materialize",
            description,
            "skip",
            False,
            "skipped with --no-git-update",
        )
    if _update_lock(ctx):
        return _step(
            "git.materialize",
            description,
            "run",
            True,
            "materialize repos before writing deps.lock",
        )
    return _step(
        "git.materialize",
        description,
        "run",
        True,
        "clone or update git repos",
    )


def _evaluate_map_folders(ctx: PrepareContext) -> PlanStep:
    return _step(
        "project.map_folders",
        "Build docker volume mapping for Odoo, venv, and addons",
        "run",
        True,
        "refresh docker volume mapping",
    )


def _evaluate_git_lock_apply(ctx: PrepareContext) -> PlanStep:
    description = "Apply pinned commits from .odpm/deps.lock.json before checkout"
    if _skip_git(ctx) or _update_lock(ctx):
        return _step(
            "git.lock_apply",
            description,
            "skip",
            False,
            "lock apply not used in this mode",
        )
    if not deps_lock_file_exists(ctx.config.project_dir):
        return _step(
            "git.lock_apply",
            description,
            "skip",
            False,
            "deps.lock.json not present",
        )
    return _step(
        "git.lock_apply",
        description,
        "run",
        True,
        "apply pinned commits from deps.lock.json",
    )


def _evaluate_template_dockerfile(ctx: PrepareContext) -> PlanStep:
    description = "Regenerate project Dockerfile from odpm template"
    if not base_image_identity_matches(ctx.config):
        return _step(
            "template.dockerfile",
            description,
            "update",
            True,
            "base image identity mismatch",
        )
    if project_template_needs_upgrade(
        ctx.config.project_dir,
        dockerfile_template_relative(ctx.config),
        constants.DOCKERFILE_TEMPLATE_MARKERS,
    ):
        return _step(
            "template.dockerfile",
            description,
            "update",
            True,
            "dockerfile template stale",
        )
    return _step(
        "template.dockerfile",
        description,
        "noop",
        True,
        "dockerfile template up to date",
    )


def _evaluate_template_dockerignore(ctx: PrepareContext) -> PlanStep:
    description = "Regenerate root .dockerignore from .odpm/dockerignore"
    if project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.DOCKERIGNORE_TEMPLATE_MARKERS,
    ):
        return _step(
            "template.dockerignore",
            description,
            "update",
            True,
            "dockerignore template stale",
        )
    return _step(
        "template.dockerignore",
        description,
        "noop",
        True,
        "dockerignore template up to date",
    )


def _evaluate_docker_engine_check(ctx: PrepareContext) -> PlanStep:
    description = "Check Docker engine and running odpm containers"
    reason = (
        "verify Docker engine and containers"
        if ctx.config.check_system
        else "check_system disabled; step still runs for compatibility"
    )
    return _step(
        "docker.engine.check",
        description,
        "run",
        ctx.config.check_system,
        reason,
    )


def _evaluate_template_odoo_conf(ctx: PrepareContext) -> PlanStep:
    description = "Regenerate .odpm/dev_odoo_docker_config_file.conf template"
    if project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        constants.ODOO_CONFIG_TEMPLATE_MARKERS,
    ):
        return _step(
            "template.odoo_conf",
            description,
            "update",
            True,
            "odoo config template stale",
        )
    return _step(
        "template.odoo_conf",
        description,
        "noop",
        True,
        "odoo config template up to date",
    )


def _evaluate_compose_template(ctx: PrepareContext) -> PlanStep:
    description = "Upgrade .odpm/docker-compose.yml project template"
    if project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.COMPOSE_TEMPLATE_MARKERS,
    ):
        return _step(
            "compose.template",
            description,
            "update",
            True,
            "compose template stale",
        )
    return _step(
        "compose.template",
        description,
        "noop",
        True,
        "compose template up to date",
    )


def _evaluate_compose_service(ctx: PrepareContext) -> PlanStep:
    description = (
        "Build compose start command and write .odpm/runtime/config.json when stale"
    )
    needs_update, svc_reason = compose_service_needs_update(ctx)
    if needs_update:
        return _step("compose.service", description, "update", True, svc_reason)
    gen_needs, gen_reason = compose_generate_needs_execute(ctx)
    if gen_needs:
        return _step(
            "compose.service",
            description,
            "run",
            True,
            f"build compose service for compose.generate ({gen_reason})",
        )
    return _step(
        "compose.service",
        description,
        "noop",
        True,
        svc_reason,
    )


def _evaluate_compose_generate(ctx: PrepareContext) -> PlanStep:
    description = "Render docker-compose.yml from project template"
    gen_needs, gen_reason = compose_generate_needs_execute(ctx)
    if gen_needs:
        return _step(
            "compose.generate",
            description,
            "update",
            True,
            gen_reason,
        )
    return _step(
        "compose.generate",
        description,
        "noop",
        True,
        gen_reason,
    )


def _evaluate_compose_validate(ctx: PrepareContext) -> PlanStep:
    description = "Validate generated docker-compose.yml"
    return _step(
        "compose.validate",
        description,
        "run",
        True,
        "validate docker-compose.yml",
    )


def _evaluate_git_checkout(ctx: PrepareContext) -> PlanStep:
    description = "Checkout dependency repos to odoo version branch"
    if _skip_git(ctx):
        return _step(
            "git.checkout",
            description,
            "skip",
            False,
            "skipped with --no-git-update",
        )
    return _step(
        "git.checkout",
        description,
        "run",
        True,
        "checkout dependency repos",
    )


def _evaluate_git_lock_collect(ctx: PrepareContext) -> PlanStep:
    description = "Collect resolved git commits and write .odpm/deps.lock.json"
    if not _update_lock(ctx):
        return _step(
            "git.lock_collect",
            description,
            "skip",
            False,
            "only used with --update-lock",
        )
    return _step(
        "git.lock_collect",
        description,
        "update",
        True,
        "write deps.lock.json from resolved commits",
    )


def _evaluate_git_lock_verify(ctx: PrepareContext) -> PlanStep:
    description = "Verify checked-out commits match deps.lock.json"
    if not _lock_verify_available(ctx):
        return _step(
            "git.lock_verify",
            description,
            "skip",
            False,
            "lock verify not applicable",
        )
    return _step(
        "git.lock_verify",
        description,
        "run",
        ctx.config.policy.is_ci(),
        "verify checked-out commits match deps.lock.json",
    )


def _evaluate_update_links(ctx: PrepareContext) -> PlanStep:
    description = "Refresh module symlinks for developing project addons"
    if not ctx.config.create_module_links:
        return _step(
            "project.update_links",
            description,
            "noop",
            False,
            "create_module_links disabled",
        )
    return _step(
        "project.update_links",
        description,
        "run",
        True,
        "refresh module symlinks",
    )


def _exec_lock_load(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.load()
    ctx.lock_manager.enter_apply_mode()


def _exec_git_ensure_present(ctx: PrepareContext) -> None:
    ctx.config.ensure_git_repos_present()


def _exec_git_materialize(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.config.materialize_git_repos(
        skip_build_date=ctx.lock_manager.has_platform_lock()
    )


def _exec_map_folders(ctx: PrepareContext) -> None:
    ctx.project_env.map_folders()


def _exec_lock_apply(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.apply_to_platform(ctx.config.odoo_platform_project)
    ctx.lock_manager.apply_to_developing(ctx.config.developing_project)
    ctx.lock_manager.apply_to_dependencies(ctx.config.dependencies_projects)


def _exec_docker_engine_check(ctx: PrepareContext) -> None:
    ctx.system_checker.check_docker()
    ctx.system_checker.check_running_containers()


def _exec_compose_template(ctx: PrepareContext) -> None:
    ctx.config.pd_manager.rebuild_docker_compose_template()


def _exec_compose_service(ctx: PrepareContext) -> None:
    ComposeServiceBuilder(ctx.config).build()


def _exec_git_checkout(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.project_env.checkout_dependencies(lock_manager=ctx.lock_manager)


def _exec_lock_collect(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.collect_and_save(developing=ctx.config.developing_project)


def _exec_lock_verify(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    if not ctx.lock_manager.apply_mode:
        return
    ctx.lock_manager.verify_after_checkout(
        platform=ctx.config.odoo_platform_project,
        developing=ctx.config.developing_project,
        dependencies=ctx.config.dependencies_projects,
    )


PREPARE_STEPS: tuple[PrepareStepDef, ...] = (
    PrepareStepDef("git.lock_load", "", _evaluate_git_lock_load, _exec_lock_load),
    PrepareStepDef(
        "git.ensure_present", "", _evaluate_git_ensure_present, _exec_git_ensure_present
    ),
    PrepareStepDef(
        "git.materialize", "", _evaluate_git_materialize, _exec_git_materialize
    ),
    PrepareStepDef(
        "project.map_folders", "", _evaluate_map_folders, _exec_map_folders
    ),
    PrepareStepDef("git.lock_apply", "", _evaluate_git_lock_apply, _exec_lock_apply),
    PrepareStepDef(
        "template.dockerfile",
        "",
        _evaluate_template_dockerfile,
        lambda ctx: ctx.project_env.generate_dockerfile(),
    ),
    PrepareStepDef(
        "template.dockerignore",
        "",
        _evaluate_template_dockerignore,
        lambda ctx: ctx.project_env.generate_dockerignore(),
    ),
    PrepareStepDef(
        "docker.engine.check", "", _evaluate_docker_engine_check, _exec_docker_engine_check
    ),
    PrepareStepDef(
        "template.odoo_conf",
        "",
        _evaluate_template_odoo_conf,
        lambda ctx: ctx.project_env.generate_config_file(),
    ),
    PrepareStepDef(
        "compose.template", "", _evaluate_compose_template, _exec_compose_template
    ),
    PrepareStepDef(
        "compose.service", "", _evaluate_compose_service, _exec_compose_service
    ),
    PrepareStepDef(
        "compose.generate",
        "",
        _evaluate_compose_generate,
        lambda ctx: ctx.project_env.generate_docker_compose_file(),
    ),
    PrepareStepDef(
        "compose.validate",
        "",
        _evaluate_compose_validate,
        lambda ctx: ctx.system_checker.check_docker_compose(),
    ),
    PrepareStepDef("git.checkout", "", _evaluate_git_checkout, _exec_git_checkout),
    PrepareStepDef(
        "git.lock_collect", "", _evaluate_git_lock_collect, _exec_lock_collect
    ),
    PrepareStepDef(
        "git.lock_verify", "", _evaluate_git_lock_verify, _exec_lock_verify
    ),
    PrepareStepDef(
        "project.update_links",
        "",
        _evaluate_update_links,
        lambda ctx: ctx.project_env.update_links(),
    ),
)


def evaluate_prepare_step(step_def: PrepareStepDef, ctx: PrepareContext) -> PlanStep:
    return step_def.evaluate(ctx)


def make_prepare_context(
    config: Config,
    project_env: CreateProjectEnvironment,
    system_checker: SystemCheckerProtocol,
    args: Namespace,
) -> PrepareContext:
    return PrepareContext(
        config=config,
        project_env=project_env,
        system_checker=system_checker,
        args=args,
        host_ctx=HostProjectContext.from_config(config, arguments=args),
    )


def collect_prepare_warnings(ctx: PrepareContext) -> tuple[str, ...]:
    warnings: list[str] = []
    if ctx.host_ctx.update_lock and ctx.host_ctx.skip_git_update:
        warnings.append("--update-lock cannot be used together with --no-git-update")
    if deps_lock_file_exists(ctx.config.project_dir) and not _skip_git(ctx) and not _update_lock(ctx):
        try:
            load_deps_lock(deps_lock_path(ctx.config.project_dir))
        except ValueError:
            warnings.append(
                "Invalid .odpm/deps.lock.json; lock verify step omitted from plan"
            )
    return tuple(warnings)


def evaluate_prepare_plan(ctx: PrepareContext) -> tuple[PlanStep, ...]:
    return tuple(step_def.evaluate(ctx) for step_def in PREPARE_STEPS)


def collect_execute_step_ids(ctx: PrepareContext) -> tuple[str, ...]:
    return tuple(
        step.id for step in evaluate_prepare_plan(ctx) if step.should_execute()
    )


def build_prepare_plan(ctx: PrepareContext) -> OdpmPlan:
    return OdpmPlan(
        steps=evaluate_prepare_plan(ctx),
        warnings=collect_prepare_warnings(ctx),
    )


def _evaluate_runtime_ci_build_image(
    config: Config, args: Namespace
) -> PlanStep | None:
    if not getattr(args, "build_image", False):
        return None
    return _step(
        "ci.build_image",
        "Build CI Docker image from prepared context",
        "run",
        True,
        "build CI image from prepared context",
    )


def _evaluate_runtime_vscode_settings(config: Config) -> PlanStep | None:
    if config.policy.skip_vscode:
        return None
    description = "Update VS Code launch and workspace settings"
    if vscode_settings_up_to_date(config):
        return _step(
            "vscode.settings",
            description,
            "noop",
            False,
            "VS Code settings already present",
        )
    return _step(
        "vscode.settings",
        description,
        "run",
        False,
        "refresh VS Code launch and settings",
    )


def _evaluate_runtime_compose_up(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> PlanStep | None:
    if not compose_up_would_run(args, host_ctx):
        return None
    description = "Run docker compose up"
    reason, _extra_warnings = evaluate_compose_up_plan(config, args)
    return _step(
        "compose.up",
        description,
        "run",
        True,
        reason,
    )


def build_runtime_plan_steps(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> tuple[PlanStep, ...]:
    steps: list[PlanStep] = []
    for evaluator in (
        lambda: _evaluate_runtime_ci_build_image(config, args),
        lambda: _evaluate_runtime_vscode_settings(config),
        lambda: _evaluate_runtime_compose_up(config, args, host_ctx),
    ):
        step = evaluator()
        if step is not None:
            steps.append(step)
    return tuple(steps)


def build_runtime_plan_warnings(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> tuple[str, ...]:
    if not compose_up_would_run(args, host_ctx):
        return ()
    _reason, extra_warnings = evaluate_compose_up_plan(config, args)
    return extra_warnings


def build_plan(config: Config, args: Namespace) -> OdpmPlan:
    ctx = make_prepare_context(
        config,
        _PlanOnlyProjectEnv(),  # type: ignore[arg-type]
        _PlanOnlySystemChecker(),  # type: ignore[arg-type]
        args,
    )
    prepare_plan = build_prepare_plan(ctx)
    runtime_steps = build_runtime_plan_steps(config, args, ctx.host_ctx)
    runtime_warnings = build_runtime_plan_warnings(config, args, ctx.host_ctx)
    return OdpmPlan(
        steps=prepare_plan.steps + runtime_steps,
        warnings=prepare_plan.warnings + runtime_warnings,
    )


class _PlanOnlyProjectEnv:
    """Unused placeholder; prepare plan evaluation reads only config and CLI args."""


class _PlanOnlySystemChecker:
    """Unused placeholder; prepare plan evaluation reads only config and CLI args."""


def validate_prepare_context(ctx: PrepareContext) -> None:
    if ctx.host_ctx.update_lock and ctx.host_ctx.skip_git_update:
        message = "--update-lock cannot be used together with --no-git-update"
        _logger.error(message)
        raise PipelineError(message, exit_code=1)


def execute_prepare(ctx: PrepareContext) -> None:
    validate_prepare_context(ctx)
    ctx.lock_manager = DepsLockManager(ctx.config)
    for step_def in PREPARE_STEPS:
        outcome = step_def.evaluate(ctx)
        if outcome.should_execute():
            step_def.execute(ctx)


# Backward-compatible alias used by contract tests.
collect_prepare_step_ids = collect_execute_step_ids
