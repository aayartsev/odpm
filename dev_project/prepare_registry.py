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
    deps_lock_file_exists,
    dockerfile_template_relative,
    project_template_needs_upgrade,
    runtime_config_stale,
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
    action: str
    required: Callable[[PrepareContext], bool]
    should_include: Callable[[PrepareContext], bool]
    execute: Callable[[PrepareContext], None]


def _skip_git(ctx: PrepareContext) -> bool:
    return ctx.host_ctx.skip_git_update


def _update_lock(ctx: PrepareContext) -> bool:
    return ctx.host_ctx.update_lock


def _include_lock_load(ctx: PrepareContext) -> bool:
    return not _skip_git(ctx) and not _update_lock(ctx)


def _include_lock_apply(ctx: PrepareContext) -> bool:
    return _include_lock_load(ctx) and deps_lock_file_exists(ctx.config.project_dir)


def _include_dockerfile_template(ctx: PrepareContext) -> bool:
    return project_template_needs_upgrade(
        ctx.config.project_dir,
        dockerfile_template_relative(ctx.config),
        constants.DOCKERFILE_TEMPLATE_MARKERS,
    ) or not base_image_identity_matches(ctx.config)


def _include_dockerignore_template(ctx: PrepareContext) -> bool:
    return project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.DOCKERIGNORE_TEMPLATE_MARKERS,
    )


def _include_odoo_conf_template(ctx: PrepareContext) -> bool:
    return project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        constants.ODOO_CONFIG_TEMPLATE_MARKERS,
    )


def _include_compose_template(ctx: PrepareContext) -> bool:
    return project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.COMPOSE_TEMPLATE_MARKERS,
    )


def _include_lock_verify(ctx: PrepareContext) -> bool:
    if _skip_git(ctx) or _update_lock(ctx):
        return False
    if not deps_lock_file_exists(ctx.config.project_dir):
        return False
    try:
        load_deps_lock(deps_lock_path(ctx.config.project_dir))
    except ValueError:
        return False
    return True


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
    PrepareStepDef(
        "git.lock_load",
        "Load .odpm/deps.lock.json and enter apply mode before checkout",
        lambda ctx: True,
        _include_lock_load,
        _exec_lock_load,
    ),
    PrepareStepDef(
        "git.ensure_present",
        "Verify local platform and developing git directories exist",
        lambda ctx: True,
        _skip_git,
        _exec_git_ensure_present,
    ),
    PrepareStepDef(
        "git.materialize",
        "Clone or update platform, developing, and dependency git repos",
        lambda ctx: True,
        lambda ctx: not _skip_git(ctx),
        _exec_git_materialize,
    ),
    PrepareStepDef(
        "project.map_folders",
        "Build docker volume mapping for Odoo, venv, and addons",
        lambda ctx: True,
        lambda ctx: True,
        _exec_map_folders,
    ),
    PrepareStepDef(
        "git.lock_apply",
        "Apply pinned commits from .odpm/deps.lock.json before checkout",
        lambda ctx: True,
        _include_lock_apply,
        _exec_lock_apply,
    ),
    PrepareStepDef(
        "template.dockerfile",
        "Regenerate project Dockerfile from odpm template",
        lambda ctx: True,
        _include_dockerfile_template,
        lambda ctx: ctx.project_env.generate_dockerfile(),
    ),
    PrepareStepDef(
        "template.dockerignore",
        "Regenerate root .dockerignore from .odpm/dockerignore",
        lambda ctx: True,
        _include_dockerignore_template,
        lambda ctx: ctx.project_env.generate_dockerignore(),
    ),
    PrepareStepDef(
        "docker.engine.check",
        "Check Docker engine and running odpm containers",
        lambda ctx: ctx.config.check_system,
        lambda ctx: True,
        _exec_docker_engine_check,
    ),
    PrepareStepDef(
        "template.odoo_conf",
        "Regenerate .odpm/dev_odoo_docker_config_file.conf template",
        lambda ctx: True,
        _include_odoo_conf_template,
        lambda ctx: ctx.project_env.generate_config_file(),
    ),
    PrepareStepDef(
        "venv.runtime_config",
        "Write .odpm/runtime/config.json (venv lock hash / scenario payload)",
        lambda ctx: True,
        lambda ctx: runtime_config_stale(ctx.config),
        _exec_compose_service,
    ),
    PrepareStepDef(
        "compose.template",
        "Upgrade .odpm/docker-compose.yml project template",
        lambda ctx: True,
        _include_compose_template,
        _exec_compose_template,
    ),
    PrepareStepDef(
        "compose.service",
        "Build compose start command and runtime config references",
        lambda ctx: True,
        lambda ctx: not runtime_config_stale(ctx.config),
        _exec_compose_service,
    ),
    PrepareStepDef(
        "compose.generate",
        "Render docker-compose.yml from project template",
        lambda ctx: True,
        lambda ctx: True,
        lambda ctx: ctx.project_env.generate_docker_compose_file(),
    ),
    PrepareStepDef(
        "compose.validate",
        "Validate generated docker-compose.yml",
        lambda ctx: True,
        lambda ctx: True,
        lambda ctx: ctx.system_checker.check_docker_compose(),
    ),
    PrepareStepDef(
        "git.checkout",
        "Checkout dependency repos to odoo version branch",
        lambda ctx: True,
        lambda ctx: not _skip_git(ctx),
        _exec_git_checkout,
    ),
    PrepareStepDef(
        "git.lock_collect",
        "Collect resolved git commits and write .odpm/deps.lock.json",
        lambda ctx: True,
        _update_lock,
        _exec_lock_collect,
    ),
    PrepareStepDef(
        "git.lock_verify",
        "Verify checked-out commits match deps.lock.json",
        lambda ctx: ctx.config.policy.is_ci(),
        _include_lock_verify,
        _exec_lock_verify,
    ),
    PrepareStepDef(
        "project.update_links",
        "Refresh module symlinks for developing project addons",
        lambda ctx: ctx.config.create_module_links,
        lambda ctx: True,
        lambda ctx: ctx.project_env.update_links(),
    ),
)


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


def collect_prepare_step_ids(ctx: PrepareContext) -> tuple[str, ...]:
    return tuple(step.id for step in PREPARE_STEPS if step.should_include(ctx))


def build_prepare_plan(ctx: PrepareContext) -> OdpmPlan:
    steps = [
        PlanStep(step.id, step.action, step.required(ctx))
        for step in PREPARE_STEPS
        if step.should_include(ctx)
    ]
    return OdpmPlan(steps=tuple(steps), warnings=collect_prepare_warnings(ctx))


def build_runtime_plan_steps(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> tuple[PlanStep, ...]:
    steps: list[PlanStep] = []
    if getattr(args, "build_image", False):
        steps.append(
            PlanStep(
                "ci.build_image",
                "Build CI Docker image from prepared context",
                True,
            )
        )
    if not config.policy.skip_vscode:
        steps.append(
            PlanStep(
                "vscode.settings",
                "Update VS Code launch and workspace settings",
                False,
            )
        )
    if (
        not getattr(args, "skip_start", False)
        and not host_ctx.update_lock
        and not getattr(args, "build_image", False)
    ):
        steps.append(
            PlanStep(
                "compose.up",
                "Run docker compose up (may add --force-recreate if stack is unhealthy)",
                True,
            )
        )
    return tuple(steps)


def build_runtime_plan_warnings(
    config: Config, args: Namespace, host_ctx: HostProjectContext
) -> tuple[str, ...]:
    warnings: list[str] = []
    if (
        not getattr(args, "skip_start", False)
        and not host_ctx.update_lock
        and not getattr(args, "build_image", False)
    ):
        warnings.append(
            "Compose stack health is checked at runtime; unhealthy stacks get --force-recreate"
        )
    return tuple(warnings)


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
    for step in PREPARE_STEPS:
        if step.should_include(ctx):
            step.execute(ctx)
