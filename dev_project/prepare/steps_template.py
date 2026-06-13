"""Project template prepare steps."""

from __future__ import annotations

from .. import constants
from ..plan import (
    PlanStep,
    dockerfile_template_relative,
    project_template_needs_upgrade,
)
from ..project_env.base_image_identity import base_image_identity_matches
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_template_dockerfile(ctx: PrepareContext) -> PlanStep:
    description = "Regenerate project Dockerfile from odpm template"
    if not base_image_identity_matches(ctx.config):
        return make_plan_step(
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
        return make_plan_step(
            "template.dockerfile",
            description,
            "update",
            True,
            "dockerfile template stale",
        )
    return make_plan_step(
        "template.dockerfile",
        description,
        "noop",
        True,
        "dockerfile template up to date",
    )


def evaluate_template_dockerignore(ctx: PrepareContext) -> PlanStep:
    description = "Regenerate root .dockerignore from .odpm/dockerignore"
    if project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.DOCKERIGNORE_TEMPLATE_MARKERS,
    ):
        return make_plan_step(
            "template.dockerignore",
            description,
            "update",
            True,
            "dockerignore template stale",
        )
    return make_plan_step(
        "template.dockerignore",
        description,
        "noop",
        True,
        "dockerignore template up to date",
    )


def evaluate_template_odoo_conf(ctx: PrepareContext) -> PlanStep:
    from ..config.odoo_conf import odoo_conf_on_disk_needs_regeneration

    description = "Regenerate project odoo.conf from .odpm template"
    template_stale = project_template_needs_upgrade(
        ctx.config.project_dir,
        constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        constants.ODOO_CONFIG_TEMPLATE_MARKERS,
    )
    conf_stale = odoo_conf_on_disk_needs_regeneration(ctx.config.path_odoo_conf)
    if template_stale or conf_stale:
        reason = (
            "odoo config template stale"
            if template_stale
            else "odoo.conf missing db settings"
        )
        return make_plan_step(
            "template.odoo_conf",
            description,
            "update",
            True,
            reason,
        )
    return make_plan_step(
        "template.odoo_conf",
        description,
        "noop",
        True,
        "odoo.conf and template up to date",
    )


def exec_template_dockerfile(ctx: PrepareContext) -> None:
    ctx.templates.generate_dockerfile()


def exec_template_dockerignore(ctx: PrepareContext) -> None:
    ctx.templates.generate_dockerignore()


def exec_template_odoo_conf(ctx: PrepareContext) -> None:
    ctx.templates.generate_config_file()
