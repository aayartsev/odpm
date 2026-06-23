"""Git and deps.lock prepare steps."""

from __future__ import annotations

from ..plan import PlanStep, deps_lock_file_exists
from ..plan.l10n import plan_msg
from .helpers import (
    lock_source_label,
    lock_verify_available,
    make_plan_step,
    manifest_lock_apply_available,
    skip_git,
    update_lock,
)
from .types import PrepareContext


def evaluate_git_lock_load(ctx: PrepareContext) -> PlanStep:
    source = lock_source_label(ctx)
    description = plan_msg(
        "Load git lock from {SOURCE} and enter apply mode before checkout",
        SOURCE=source,
    )
    if skip_git(ctx):
        return make_plan_step(
            "git.lock_load",
            description,
            "skip",
            False,
            plan_msg("skipped with --no-git-update"),
        )
    if update_lock(ctx):
        return make_plan_step(
            "git.lock_load",
            description,
            "skip",
            False,
            plan_msg("skipped with --update-lock"),
        )
    return make_plan_step(
        "git.lock_load",
        description,
        "run",
        True,
        plan_msg("load git lock from {SOURCE} before checkout", SOURCE=source),
    )


def evaluate_git_ensure_present(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Verify local platform and developing git directories exist")
    if not skip_git(ctx):
        return make_plan_step(
            "git.ensure_present",
            description,
            "skip",
            False,
            plan_msg("git repos will be materialized"),
        )
    return make_plan_step(
        "git.ensure_present",
        description,
        "run",
        True,
        plan_msg("verify local git directories exist"),
    )


def evaluate_git_materialize(ctx: PrepareContext) -> PlanStep:
    description = plan_msg(
        "Clone or update platform, developing, and dependency git repos"
    )
    if skip_git(ctx):
        return make_plan_step(
            "git.materialize",
            description,
            "skip",
            False,
            plan_msg("skipped with --no-git-update"),
        )
    if update_lock(ctx):
        return make_plan_step(
            "git.materialize",
            description,
            "run",
            True,
            plan_msg("materialize repos before writing deps.lock"),
        )
    return make_plan_step(
        "git.materialize",
        description,
        "run",
        True,
        plan_msg("clone or update git repos"),
    )


def evaluate_git_lock_apply(ctx: PrepareContext) -> PlanStep:
    source = lock_source_label(ctx)
    description = plan_msg("Apply pinned commits from {SOURCE} before checkout", SOURCE=source)
    if skip_git(ctx) or update_lock(ctx):
        return make_plan_step(
            "git.lock_apply",
            description,
            "skip",
            False,
            plan_msg("lock apply not used in this mode"),
        )
    if (
        not deps_lock_file_exists(ctx.host_ctx.project_dir)
        and not manifest_lock_apply_available(ctx)
    ):
        return make_plan_step(
            "git.lock_apply",
            description,
            "skip",
            False,
            plan_msg("no git lock source available"),
        )
    return make_plan_step(
        "git.lock_apply",
        description,
        "run",
        True,
        plan_msg("apply pinned commits from {SOURCE}", SOURCE=source),
    )


def evaluate_git_checkout(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Checkout dependency repos to odoo version branch")
    if skip_git(ctx):
        return make_plan_step(
            "git.checkout",
            description,
            "skip",
            False,
            plan_msg("skipped with --no-git-update"),
        )
    return make_plan_step(
        "git.checkout",
        description,
        "run",
        True,
        plan_msg("checkout dependency repos"),
    )


def evaluate_git_lock_collect(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Collect resolved git commits and write .odpm/deps.lock.json")
    if not update_lock(ctx):
        return make_plan_step(
            "git.lock_collect",
            description,
            "skip",
            False,
            plan_msg("only used with --update-lock"),
        )
    return make_plan_step(
        "git.lock_collect",
        description,
        "update",
        True,
        plan_msg("write deps.lock.json from resolved commits"),
    )


def evaluate_git_lock_verify(ctx: PrepareContext) -> PlanStep:
    source = lock_source_label(ctx)
    description = plan_msg("Verify checked-out commits match {SOURCE}", SOURCE=source)
    if not lock_verify_available(ctx):
        return make_plan_step(
            "git.lock_verify",
            description,
            "skip",
            False,
            plan_msg("lock verify not applicable"),
        )
    return make_plan_step(
        "git.lock_verify",
        description,
        "run",
        ctx.host_ctx.policy.is_ci(),
        plan_msg("verify checked-out commits match {SOURCE}", SOURCE=source),
    )


def exec_lock_load(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.load()
    ctx.lock_manager.enter_apply_mode()


def exec_git_ensure_present(ctx: PrepareContext) -> None:
    ctx.git_repos.ensure_git_repos_present()


def exec_git_materialize(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.git_repos.materialize_git_repos(
        skip_build_date=ctx.lock_manager.has_platform_lock()
    )


def exec_lock_apply(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.apply_pinned_locks()


def exec_git_checkout(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.links.checkout_dependencies(lock_manager=ctx.lock_manager)


def exec_lock_collect(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    ctx.lock_manager.collect_and_save_from_config()


def exec_lock_verify(ctx: PrepareContext) -> None:
    assert ctx.lock_manager is not None
    if not ctx.lock_manager.apply_mode:
        return
    ctx.lock_manager.verify_pinned_checkout()
