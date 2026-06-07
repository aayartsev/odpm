"""Typed host CLI arguments for odpm."""

from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class OdpmCliArgs:
    """Frozen snapshot of host-side odpm CLI flags."""

    init: str | None = None
    build_image: bool = False
    image_tag: str | None = None
    get_dbs_list: str | None = None
    start_precommit: bool = False
    set_admin_pass: bool | str | None = None
    translate: str | None = None
    db_drop: bool = False
    db_restore: str | None = None
    db_backup: bool | str | None = None
    d: str | None = None
    i: bool = False
    u: bool = False
    test: bool = False
    branch: str | None = None
    screencasts: bool = False
    odoo_version: str | None = None
    sql_execute: str | None = None
    export_po_files: str | None = None
    version: bool = False
    odoo_git_link: str | None = None
    platform_name: str | None = None
    python_version: str | None = None
    distro_version: str | None = None
    distro_name: str | None = None
    postgres_version: str | None = None
    requirements_txt: str = ""
    odoo_build_date: str | None = None
    plan: bool = False
    plan_no_docker: bool = False
    plan_show_diff: bool = False
    plan_format: str = "table"
    plan_strict: bool = False
    skip_start: bool | None = None
    no_git_update: bool = False
    update_lock: bool = False
    odoo_bin: list[str] | None = None
    command: str | None = None
    scaffold_module_name: str | None = None
    scaffold_template_name: str | None = None

    @classmethod
    def from_namespace(cls, ns: Namespace) -> OdpmCliArgs:
        kwargs = {
            field.name: getattr(ns, field.name, field.default) for field in fields(cls)
        }
        return cls(**kwargs)
