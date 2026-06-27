"""Compose template and generation prepare steps."""

from __future__ import annotations

from .. import constants
from ..plan import PlanStep, project_template_needs_upgrade
from ..plan.compose_preview import (
    compose_generate_needs_execute,
    compose_service_needs_update,
)
from ..plan.l10n import plan_msg
from ..system_check_policy import SystemCheckPolicy
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_compose_template(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Upgrade .odpm/docker-compose.yml project template")
    if project_template_needs_upgrade(
        ctx.host_ctx.project_dir,
        constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.COMPOSE_TEMPLATE_MARKERS,
    ):
        return make_plan_step(
            "compose.template",
            description,
            "update",
            True,
            plan_msg("compose template stale"),
        )
    return make_plan_step(
        "compose.template",
        description,
        "noop",
        True,
        plan_msg("compose template up to date"),
    )


def evaluate_compose_fragments(ctx: PrepareContext) -> PlanStep:
    from ..compose.fragments import collect_compose_services, compose_fragments_need_materialize

    description = plan_msg("Materialize manifest and plugin compose service fragments")
    services = collect_compose_services(ctx.extension_host())
    odpm_scenario = ctx.host_ctx.user_env.odpm_scenario
    if compose_fragments_need_materialize(
        ctx.host_ctx.project_dir,
        services,
        odpm_scenario=odpm_scenario,
    ):
        reason = (
            plan_msg("compose service fragments stale")
            if services
            else plan_msg("compose service fragments cleanup")
        )
        return make_plan_step(
            "compose.fragments",
            description,
            "update",
            True,
            reason,
        )
    return make_plan_step(
        "compose.fragments",
        description,
        "noop",
        True,
        plan_msg("compose service fragments up to date"),
    )


def evaluate_compose_service(ctx: PrepareContext) -> PlanStep:
    description = plan_msg(
        "Build compose start command and write .odpm/runtime/config.json when stale"
    )
    needs_update, svc_reason = compose_service_needs_update(ctx)
    if needs_update:
        return make_plan_step(
            "compose.service", description, "update", True, plan_msg(svc_reason)
        )
    gen_needs, gen_reason = compose_generate_needs_execute(ctx)
    if gen_needs:
        return make_plan_step(
            "compose.service",
            description,
            "run",
            True,
            plan_msg(
                "build compose service for compose.generate ({REASON})",
                REASON=gen_reason,
            ),
        )
    return make_plan_step(
        "compose.service",
        description,
        "noop",
        True,
        plan_msg(svc_reason),
    )


def evaluate_compose_generate(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Render docker-compose.yml from project template")
    gen_needs, gen_reason = compose_generate_needs_execute(ctx)
    if gen_needs:
        return make_plan_step(
            "compose.generate",
            description,
            "update",
            True,
            plan_msg(gen_reason),
        )
    return make_plan_step(
        "compose.generate",
        description,
        "noop",
        True,
        plan_msg(gen_reason),
    )


def evaluate_compose_validate(ctx: PrepareContext) -> PlanStep:
    description = plan_msg("Validate generated docker-compose.yml")
    policy = SystemCheckPolicy.from_host_context(ctx.host_ctx)
    if not policy.compose_validate:
        return make_plan_step(
            "compose.validate",
            description,
            "skip",
            True,
            plan_msg("compose validation disabled by policy"),
        )
    return make_plan_step(
        "compose.validate",
        description,
        "run",
        True,
        plan_msg("validate docker-compose.yml"),
    )


def exec_compose_template(ctx: PrepareContext) -> None:
    ctx.rebuild_compose_template()


def exec_compose_fragments(ctx: PrepareContext) -> None:
    from ..compose.fragments import collect_compose_services, materialize_compose_fragments

    services = collect_compose_services(ctx.extension_host())
    materialize_compose_fragments(
        ctx.host_ctx.project_dir,
        services,
        odpm_scenario=ctx.host_ctx.user_env.odpm_scenario,
    )


def exec_compose_service(ctx: PrepareContext) -> None:
    ctx.build_compose_service()


def exec_compose_generate(ctx: PrepareContext) -> None:
    from ..docker_capabilities import cached_docker_capabilities, probe_docker_capabilities
    from ..subprocess_runner import run_checked

    config = ctx.config
    if cached_docker_capabilities(config) is None:
        config.docker_capabilities = probe_docker_capabilities(
            config.docker_compose_command,
            run_checked=run_checked,
        )
    ctx.compose_generator.generate_docker_compose_file()


def exec_compose_validate(ctx: PrepareContext) -> None:
    import os

    from ..compose.validate import validate_compose_file

    ctx.system_checker.check_docker_compose()
    validate_compose_file(os.path.join(ctx.host_ctx.project_dir, "docker-compose.yml"))
