"""Logical group headers for ``odpm plan`` table output (labels only)."""

from __future__ import annotations

from ..translations import _


# step id → stable group key (emit header once per key when first seen)
_STEP_GROUP_KEYS: dict[str, str] = {
    "git.lock_load": "git_sources",
    "git.ensure_present": "git_sources",
    "git.materialize_developing": "git_sources",
    "git.materialize_platform": "git_sources",
    "sources.materialize": "git_sources",
    "hooks.post_clone": "post_clone",
    "git.materialize_dependencies": "dependencies",
    "project.map_folders": "project_layout",
    "git.lock_apply": "lock_pins",
    "template.dockerfile": "templates_compose",
    "template.dockerignore": "templates_compose",
    "docker.engine.check": "templates_compose",
    "docker.ports.release": "templates_compose",
    "template.odoo_conf": "templates_compose",
    "database.drift": "templates_compose",
    "compose.template": "templates_compose",
    "compose.fragments": "templates_compose",
    "compose.service": "templates_compose",
    "compose.generate": "templates_compose",
    "compose.validate": "templates_compose",
    "secrets.fetch": "secrets",
    "secrets.materialize": "secrets",
    "git.checkout": "checkout_links",
    "git.lock_collect": "checkout_links",
    "git.lock_verify": "checkout_links",
    "project.update_links": "checkout_links",
    "compose.up": "runtime",
    "ide.debug_profile": "ide",
    "image.base": "image_build",
    "image.platform": "image_build",
    "image.deps": "image_build",
    "image.app": "image_build",
    "image.lint": "image_build",
    "ci.build_image": "image_build",
}


def plan_group_key_for_step(step_id: str) -> str | None:
    return _STEP_GROUP_KEYS.get(step_id)


def plan_group_header(group_key: str) -> str:
    # Literals must appear as _("...") for scripts/check_i18n_catalog.py.
    if group_key == "git_sources":
        return _("Plan group: preparation — git and sources")
    if group_key == "post_clone":
        return _("Plan group: post-clone hooks")
    if group_key == "dependencies":
        return _("Plan group: dependencies")
    if group_key == "project_layout":
        return _("Plan group: project layout")
    if group_key == "lock_pins":
        return _("Plan group: lock pins")
    if group_key == "templates_compose":
        return _("Plan group: templates and compose")
    if group_key == "secrets":
        return _("Plan group: secrets")
    if group_key == "checkout_links":
        return _("Plan group: checkout and project links")
    if group_key == "runtime":
        return _("Plan group: runtime")
    if group_key == "ide":
        return _("Plan group: IDE")
    if group_key == "image_build":
        return _("Plan group: image build")
    return group_key
