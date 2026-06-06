"""Git and deps.lock prepare steps."""

from __future__ import annotations

from ..plan import PlanStep, deps_lock_file_exists
from .helpers import lock_verify_available, make_plan_step, skip_git, update_lock
from .types import PrepareContext


def evaluate_git_lock_load(ctx: PrepareContext) -> PlanStep:
    description = "Load .odpm/deps.lock.json and enter apply mode before checkout"
    if skip_git(ctx):
        return make_plan_step(
            "git.lock_load",
            description,
            "skip",
            False,
            "skipped with --no-git-update",
        )
    if update_lock(ctx):
        return make_plan_step(
            "git.lock_load",
            description,
            "skip",
            False,
            "skipped with --update-lock",
        )
    return make_plan_step(
        "git.lock_load",
        description,
        "run",
        True,
        "load deps.lock before checkout",
    )


def evaluate_git_ensure_present(ctx: PrepareContext) -> PlanStep:
    description = "Verify local platform and developing git directories exist"
    if not skip_git(ctx):
        return make_plan_step(
            "git.ensure_present",
            description,
            "skip",
            False,
            "git repos will be materialized",
        )
    return make_plan_step(
        "git.ensure_present",
        description,
        "run",
        True,
        "verify local git directories exist",
    )


def evaluate_git_materialize(ctx: PrepareContext) -> PlanStep:
    description = "Clone or update platform, developing, and dependency git repos"
    if skip_git(ctx):
        return make_plan_step(
            "git.materialize",
            description,
            "skip",
            False,
            "skipped with --no-git-update",
        )
    if update_lock(ctx):
        return make_plan_step(
            "git.materialize",
            description,
            "run",
            True,
            "materialize repos before writing deps.lock",
        )
    return make_plan_step(
        "git.materialize",
        description,
        "run",
        True,
        "clone or update git repos",
    )


def evaluate_git_lock_apply(ctx: PrepareContext) -> PlanStep:
    description = "Apply pinned commits from .odpm/deps.lock.json before checkout"
    if skip_git(ctx) or update_lock(ctx):
        return make_plan_step(
            "git.lock_apply",
            description,
            "skip",
            False,
            "lock apply not used in this mode",
        )
    if not deps_lock_file_exists(ctx.config.project_dir):
        return make_plan_step(
            "git.lock_apply",
            description,
            "skip",
            False,
            "deps.lock.json not present",
        )
    return make_plan_step(
        "git.lock_apply",
        description,
        "run",
        True,
        "apply pinned commits from deps.lock.json",
    )


def evaluate_git_checkout(ctx: PrepareContext) -> PlanStep:
    description = "Checkout dependency repos to odoo version branch"
    if skip_git(ctx):
        return make_plan_step(
            "git.checkout",
            description,
            "skip",
            False,
            "skipped with --no-git-update",
        )
    return make_plan_step(
        "git.checkout",
        description,
        "run",
        True,
        "checkout dependency repos",
    )


def evaluate_git_lock_collect(ctx: PrepareContext) -> PlanStep:
    description = "Collect resolved git commits and write .odpm/deps.lock.json"
    if not update_lock(ctx):
        return make_plan_step(
            "git.lock_collect",
            description,
            "skip",
            False,
            "only used with --update-lock",
        )
    return make_plan_step(
        "git.lock_collect",
        description,
        "update",
        True,
        "write deps.lock.json from resolved commits",
    )


def evaluate_git_lock_verify(ctx: PrepareContext) -> PlanStep:
    description = "Verify checked-out commits match deps.lock.json"
    if not lock_verify_available(ctx):
        return make_plan_step(
            "git.lock_verify",
            description,
            "skip",
            False,
            "lock verify not applicable",
        )
    return make_plan_step(
        "git.lock_verify",
        description,
        "run",
        ctx.config.policy.is_ci(),
        "verify checked-out commits match deps.lock.json",
    )


def exec_lock_load(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.load()
    ctx.lock_manager.enter_apply_mode()


def exec_git_ensure_present(ctx: PrepareContext) -> None:
    ctx.config.ensure_git_repos_present()


def exec_git_materialize(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.config.materialize_git_repos(
        skip_build_date=ctx.lock_manager.has_platform_lock()
    )


def exec_lock_apply(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.apply_to_platform(ctx.config.odoo_platform_project)
    ctx.lock_manager.apply_to_developing(ctx.config.developing_project)
    ctx.lock_manager.apply_to_dependencies(ctx.config.dependencies_projects)


def exec_git_checkout(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.project_env.checkout_dependencies(lock_manager=ctx.lock_manager)


def exec_lock_collect(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.collect_and_save(developing=ctx.config.developing_project)


def exec_lock_verify(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    if not ctx.lock_manager.apply_mode:
        return
    ctx.lock_manager.verify_after_checkout(
        platform=ctx.config.odoo_platform_project,
        developing=ctx.config.developing_project,
        dependencies=ctx.config.dependencies_projects,
    )
