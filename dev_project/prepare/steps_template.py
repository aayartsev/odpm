"""Project template prepare steps."""

from __future__ import annotations

from .. import constants
from ..plan import (
    PlanStep,
    dockerfile_template_relative_host,
    project_template_needs_upgrade,
)
from ..project_env.base_image_identity import base_image_identity_matches_host
from .helpers import make_plan_step
from .types import PrepareContext


def evaluate_template_dockerfile(ctx: PrepareContext) -> PlanStep:
    description = "Regenerate project Dockerfile from odpm template"
    if not base_image_identity_matches_host(ctx.host_ctx):
        return make_plan_step(
            "template.dockerfile",
            description,
            "update",
            True,
            "base image identity mismatch",
        )
    if project_template_needs_upgrade(
        ctx.host_ctx.project_dir,
        dockerfile_template_relative_host(ctx.host_ctx),
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
        ctx.host_ctx.project_dir,
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
    from ..config.odoo_conf import (
        odoo_conf_db_host_mismatch,
        odoo_conf_on_disk_needs_regeneration,
    )
    from ..translations import _

    description = "Regenerate project odoo.conf from .odpm template"
    expected_host = ctx.host_ctx.user_env.postgres_service_name
    template_stale = project_template_needs_upgrade(
        ctx.host_ctx.project_dir,
        constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        constants.ODOO_CONFIG_TEMPLATE_MARKERS,
    )
    path_odoo_conf = ctx.host_ctx.docker_layout.path_odoo_conf
    conf_stale = odoo_conf_on_disk_needs_regeneration(
        path_odoo_conf,
        expected_db_host=expected_host,
    )
    if template_stale or conf_stale:
        if template_stale:
            reason = "odoo config template stale"
        elif odoo_conf_db_host_mismatch(path_odoo_conf, expected_host):
            reason = _(
                "odoo.conf db_host out of sync with postgres service ({EXPECTED})"
            ).format(EXPECTED=expected_host)
        else:
            reason = "odoo.conf missing db settings"
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
