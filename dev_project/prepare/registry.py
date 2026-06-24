"""Ordered prepare-step registry shared by plan and materializer."""

from __future__ import annotations

from .steps_compose import (
    evaluate_compose_fragments,
    evaluate_compose_generate,
    evaluate_compose_service,
    evaluate_compose_template,
    evaluate_compose_validate,
    exec_compose_fragments,
    exec_compose_generate,
    exec_compose_service,
    exec_compose_template,
    exec_compose_validate,
)
from .steps_database import evaluate_database_drift, exec_database_drift
from .steps_secrets import evaluate_secrets_materialize, exec_secrets_materialize
from .steps_docker import (
    evaluate_docker_engine_check,
    evaluate_docker_ports_release,
    exec_docker_engine_check,
    exec_docker_ports_release,
)
from .steps_hooks import evaluate_hooks_post_clone, exec_hooks_post_clone
from .steps_git import (
    evaluate_git_checkout,
    evaluate_git_ensure_present,
    evaluate_git_lock_apply,
    evaluate_git_lock_collect,
    evaluate_git_lock_load,
    evaluate_git_lock_verify,
    evaluate_git_materialize,
    exec_git_checkout,
    exec_git_ensure_present,
    exec_git_materialize,
    exec_lock_apply,
    exec_lock_collect,
    exec_lock_load,
    exec_lock_verify,
)
from .steps_project import (
    evaluate_map_folders,
    evaluate_update_links,
    exec_map_folders,
    exec_update_links,
)
from .steps_template import (
    evaluate_template_dockerfile,
    evaluate_template_dockerignore,
    evaluate_template_odoo_conf,
    exec_template_dockerfile,
    exec_template_dockerignore,
    exec_template_odoo_conf,
)
from .types import PrepareStepDef

BUILTIN_PREPARE_STEPS: tuple[PrepareStepDef, ...] = (
    PrepareStepDef("git.lock_load", "", evaluate_git_lock_load, exec_lock_load),
    PrepareStepDef(
        "git.ensure_present", "", evaluate_git_ensure_present, exec_git_ensure_present
    ),
    PrepareStepDef(
        "git.materialize", "", evaluate_git_materialize, exec_git_materialize
    ),
    PrepareStepDef(
        "hooks.post_clone", "", evaluate_hooks_post_clone, exec_hooks_post_clone
    ),
    PrepareStepDef(
        "project.map_folders", "", evaluate_map_folders, exec_map_folders
    ),
    PrepareStepDef("git.lock_apply", "", evaluate_git_lock_apply, exec_lock_apply),
    PrepareStepDef(
        "template.dockerfile",
        "",
        evaluate_template_dockerfile,
        exec_template_dockerfile,
    ),
    PrepareStepDef(
        "template.dockerignore",
        "",
        evaluate_template_dockerignore,
        exec_template_dockerignore,
    ),
    PrepareStepDef(
        "docker.engine.check", "", evaluate_docker_engine_check, exec_docker_engine_check
    ),
    PrepareStepDef(
        "docker.ports.release",
        "",
        evaluate_docker_ports_release,
        exec_docker_ports_release,
    ),
    PrepareStepDef(
        "template.odoo_conf",
        "",
        evaluate_template_odoo_conf,
        exec_template_odoo_conf,
    ),
    PrepareStepDef(
        "database.drift", "", evaluate_database_drift, exec_database_drift
    ),
    PrepareStepDef(
        "compose.template", "", evaluate_compose_template, exec_compose_template
    ),
    PrepareStepDef(
        "compose.fragments",
        "",
        evaluate_compose_fragments,
        exec_compose_fragments,
    ),
    PrepareStepDef(
        "secrets.materialize",
        "",
        evaluate_secrets_materialize,
        exec_secrets_materialize,
    ),
    PrepareStepDef(
        "compose.service", "", evaluate_compose_service, exec_compose_service
    ),
    PrepareStepDef(
        "compose.generate",
        "",
        evaluate_compose_generate,
        exec_compose_generate,
    ),
    PrepareStepDef(
        "compose.validate",
        "",
        evaluate_compose_validate,
        exec_compose_validate,
    ),
    PrepareStepDef("git.checkout", "", evaluate_git_checkout, exec_git_checkout),
    PrepareStepDef(
        "git.lock_collect", "", evaluate_git_lock_collect, exec_lock_collect
    ),
    PrepareStepDef(
        "git.lock_verify", "", evaluate_git_lock_verify, exec_lock_verify
    ),
    PrepareStepDef(
        "project.update_links",
        "",
        evaluate_update_links,
        exec_update_links,
    ),
)


def get_prepare_steps() -> tuple[PrepareStepDef, ...]:
    """Built-in prepare steps plus pluggy/entry-point extensions."""
    from ..extensions.registry import get_prepare_steps as merge_extension_prepare_steps

    return merge_extension_prepare_steps(BUILTIN_PREPARE_STEPS)


# Backward-compatible alias: built-in steps only (extension steps via get_prepare_steps()).
PREPARE_STEPS = BUILTIN_PREPARE_STEPS
