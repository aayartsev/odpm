"""Compose template and generation prepare steps."""

from __future__ import annotations

from .. import constants
from ..plan import PlanStep, project_template_needs_upgrade
from ..system_check_policy import SystemCheckPolicy
from ..compose.service_builder import ComposeServiceBuilder
from ..plan.compose_preview import (
    compose_generate_needs_execute,
    compose_service_needs_update,
)
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_compose_template(ctx: PrepareContext) -> PlanStep:
    description = "Upgrade .odpm/docker-compose.yml project template"
    if project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.COMPOSE_TEMPLATE_MARKERS,
    ):
        return make_plan_step(
            "compose.template",
            description,
            "update",
            True,
            "compose template stale",
        )
    return make_plan_step(
        "compose.template",
        description,
        "noop",
        True,
        "compose template up to date",
    )


def evaluate_compose_service(ctx: PrepareContext) -> PlanStep:
    description = (
        "Build compose start command and write .odpm/runtime/config.json when stale"
    )
    needs_update, svc_reason = compose_service_needs_update(ctx)
    if needs_update:
        return make_plan_step("compose.service", description, "update", True, svc_reason)
    gen_needs, gen_reason = compose_generate_needs_execute(ctx)
    if gen_needs:
        return make_plan_step(
            "compose.service",
            description,
            "run",
            True,
            f"build compose service for compose.generate ({gen_reason})",
        )
    return make_plan_step(
        "compose.service",
        description,
        "noop",
        True,
        svc_reason,
    )


def evaluate_compose_generate(ctx: PrepareContext) -> PlanStep:
    description = "Render docker-compose.yml from project template"
    gen_needs, gen_reason = compose_generate_needs_execute(ctx)
    if gen_needs:
        return make_plan_step(
            "compose.generate",
            description,
            "update",
            True,
            gen_reason,
        )
    return make_plan_step(
        "compose.generate",
        description,
        "noop",
        True,
        gen_reason,
    )


def evaluate_compose_validate(ctx: PrepareContext) -> PlanStep:
    description = "Validate generated docker-compose.yml"
    policy = SystemCheckPolicy.from_config(ctx.config)
    if not policy.compose_validate:
        return make_plan_step(
            "compose.validate",
            description,
            "skip",
            True,
            "compose validation disabled by policy",
        )
    return make_plan_step(
        "compose.validate",
        description,
        "run",
        True,
        "validate docker-compose.yml",
    )


def exec_compose_template(ctx: PrepareContext) -> None:
    ctx.config.pd_manager.rebuild_docker_compose_template()


def exec_compose_service(ctx: PrepareContext) -> None:
    ComposeServiceBuilder(ctx.config).build()


def exec_compose_generate(ctx: PrepareContext) -> None:
    ctx.compose_generator.generate_docker_compose_file()
