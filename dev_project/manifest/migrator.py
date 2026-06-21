"""Transform flat manifest v1 → nested manifest v2."""

from __future__ import annotations

import json
from typing import Any

from .. import constants
from ..errors import ConfigError
from ..git.deps_lock import DepsLock
from ..translations import _
from .compat import parse_manifest_version_info
from .database import database_block_from_user_settings
from .locks import manifest_locks_from_deps_lock
from .schema import validate_manifest_v2


def migrate_v1_flat_to_v2(
    v1_raw: dict[str, Any],
    *,
    user_settings: dict[str, Any] | None = None,
    deps_lock: DepsLock | None = None,
) -> dict[str, Any]:
    """Build nested manifest v2 from flat v1 ``odpm.json`` content."""
    info = parse_manifest_version_info(v1_raw)
    if info.manifest_schema == constants.MANIFEST_SCHEMA_V2:
        raise ConfigError(_("Manifest is already manifest_schema 2."))

    platform_git = str(v1_raw.get("odoo_git_link", constants.ODOO_GIT_LINK))
    platform: dict[str, Any] = {"git": platform_git}
    build_date = v1_raw.get("odoo_build_date", constants.ODOO_DEFAULT_BUILD_DATE)
    if build_date:
        platform["build_date"] = str(build_date)

    v2: dict[str, Any] = {
        "manifest_schema": constants.MANIFEST_SCHEMA_V2,
        "requires_odpm": constants.ODPM_VERSION,
        "platform": platform,
        "python": str(v1_raw.get("python_version", constants.DEFAULT_PYTHON_VERSION)),
        "distro": {
            "name": str(v1_raw.get("distro_name", constants.DEFAULT_DISTRO_NAME)),
            "version": str(
                v1_raw.get("distro_version", constants.DEFAULT_DISTRO_VERSION)
            ),
        },
        "postgres": str(
            v1_raw.get("postgres_version", constants.DEFAULT_POSTGRES_VERSION)
        ),
        "dependencies": list(v1_raw.get("dependencies") or []),
        "requirements": list(v1_raw.get("requirements_txt") or []),
    }

    odoo_version = v1_raw.get("odoo_version")
    if odoo_version is not None and odoo_version != "":
        v2["odoo_version"] = odoo_version

    platform_name = v1_raw.get("platform_name")
    if platform_name:
        v2["platform_name"] = platform_name
    arch = v1_raw.get("arch")
    if arch:
        v2["arch"] = arch

    database = v1_raw.get("database")
    if isinstance(database, dict):
        v2["database"] = dict(database)
    elif user_settings:
        database_block = database_block_from_user_settings(user_settings)
        if database_block:
            v2["database"] = database_block

    developing_git = v1_raw.get("developing_project")
    if not developing_git and user_settings:
        developing_git = user_settings.get("developing_project")
    if developing_git and str(developing_git).strip():
        v2["developing"] = {"git": str(developing_git).strip()}

    if deps_lock is not None:
        locks = manifest_locks_from_deps_lock(deps_lock)
        if locks:
            v2["locks"] = locks

    validate_manifest_v2(v2)
    return v2


def format_manifest_migration_diff(
    path: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> str:
    """Return unified diff between two manifest JSON documents."""
    from ..plan.diff import _make_unified_diff

    old_text = json.dumps(before, indent=4, ensure_ascii=False) + "\n"
    new_text = json.dumps(after, indent=4, ensure_ascii=False) + "\n"
    return _make_unified_diff(path, old_text, new_text)
