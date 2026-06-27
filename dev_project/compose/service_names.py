"""Compose logical vs physical service naming (4.7 prefix track)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .. import constants
from ..logging import get_module_logger
from ..translations import _

_logger = get_module_logger(__name__)

LOGICAL_DB = constants.DATABASE_NAME_INSTANCE
LOGICAL_ODOO = "odoo"
LOGICAL_POSTGRES_VOLUME = "postgres-data"

_VALID_COMPOSE_PREFIX = re.compile(r"^[a-z][a-z0-9-]*$")


def parse_compose_prefix(raw: str | None) -> str | None:
    """Return canonical prefix with trailing ``-``, or ``None`` when unset/invalid."""
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if not _VALID_COMPOSE_PREFIX.fullmatch(value):
        _logger.warning(
            _(
                "Invalid {ENV}=%r (use lowercase letters, digits, '-'; "
                "must start with a letter); prefix disabled"
            ).format(ENV=constants.ODPM_COMPOSE_PREFIX_ENV, VALUE=raw),
        )
        return None
    return value if value.endswith("-") else f"{value}-"


def compose_project_name_from_prefix(prefix_with_dash: str) -> str:
    """Docker Compose project slug (no trailing ``-``)."""
    return prefix_with_dash.rstrip("-")


@dataclass(frozen=True)
class ComposeNamingContext:
    """Resolved physical compose names for the active ``.env``."""

    compose_prefix: str | None
    compose_project_name: str | None
    postgres_service_name: str
    odoo_service_name: str
    postgres_volume_name: str

    @property
    def uses_prefix(self) -> bool:
        return self.compose_prefix is not None


def resolve_compose_naming(
    *,
    compose_prefix_raw: str | None,
    legacy_postgres_service_name: str,
) -> ComposeNamingContext:
    """Build physical service/volume/project names from prefix and legacy postgres name."""
    prefix = parse_compose_prefix(compose_prefix_raw)
    if prefix is None:
        return ComposeNamingContext(
            compose_prefix=None,
            compose_project_name=None,
            postgres_service_name=legacy_postgres_service_name,
            odoo_service_name=LOGICAL_ODOO,
            postgres_volume_name=LOGICAL_POSTGRES_VOLUME,
        )

    legacy_raw = legacy_postgres_service_name
    if legacy_raw != constants.DEFAULT_POSTGRES_SERVICE_NAME:
        _logger.warning(
            _(
                "{PREFIX_ENV} is set; ignoring {LEGACY_ENV}=%r "
                "(postgres service will be {DB_NAME})"
            ).format(
                PREFIX_ENV=constants.ODPM_COMPOSE_PREFIX_ENV,
                LEGACY_ENV=constants.POSTGRES_SERVICE_NAME_ENV,
                VALUE=legacy_raw,
                DB_NAME=f"{prefix}{LOGICAL_DB}",
            ),
        )

    return ComposeNamingContext(
        compose_prefix=prefix,
        compose_project_name=compose_project_name_from_prefix(prefix),
        postgres_service_name=f"{prefix}{LOGICAL_DB}",
        odoo_service_name=f"{prefix}{LOGICAL_ODOO}",
        postgres_volume_name=f"{prefix}{LOGICAL_POSTGRES_VOLUME}",
    )


def compose_naming_from_user_env(user_env) -> ComposeNamingContext:
    """Build naming context from ``CreateUserEnvironment`` / ``ParsedUserEnv`` fields."""
    compose_prefix = getattr(user_env, "compose_prefix", None)
    if not isinstance(compose_prefix, str) or not compose_prefix:
        compose_prefix = None
    compose_project_name = getattr(user_env, "compose_project_name", None)
    if not isinstance(compose_project_name, str) or not compose_project_name:
        compose_project_name = None

    def _str_attr(attr: str, default: str) -> str:
        value = getattr(user_env, attr, None)
        if isinstance(value, str) and value:
            return value
        return default

    return ComposeNamingContext(
        compose_prefix=compose_prefix,
        compose_project_name=compose_project_name,
        postgres_service_name=_str_attr("postgres_service_name", LOGICAL_DB),
        odoo_service_name=_str_attr("odoo_service_name", LOGICAL_ODOO),
        postgres_volume_name=_str_attr("postgres_volume_name", LOGICAL_POSTGRES_VOLUME),
    )


def _map_logical_service_name(name: str, ctx: ComposeNamingContext) -> str:
    if name == LOGICAL_DB:
        return ctx.postgres_service_name
    if name == LOGICAL_ODOO:
        return ctx.odoo_service_name
    return name


def _rewrite_service_name_list(
    items: list[Any], ctx: ComposeNamingContext
) -> list[Any]:
    rewritten: list[Any] = []
    for item in items:
        if isinstance(item, str):
            rewritten.append(_map_logical_service_name(item, ctx))
        else:
            rewritten.append(item)
    return rewritten


def _rewrite_volume_mount(mount: Any, ctx: ComposeNamingContext) -> Any:
    if not isinstance(mount, str) or not ctx.uses_prefix:
        return mount
    parts = mount.split(":", 2)
    if parts and parts[0] == LOGICAL_POSTGRES_VOLUME:
        parts[0] = ctx.postgres_volume_name
        return ":".join(parts)
    return mount


def _rewrite_service_spec(spec: dict[str, Any], ctx: ComposeNamingContext) -> dict[str, Any]:
    updated = dict(spec)
    for field in ("depends_on", "links"):
        value = updated.get(field)
        if isinstance(value, list):
            updated[field] = _rewrite_service_name_list(value, ctx)
    volumes = updated.get("volumes")
    if isinstance(volumes, list):
        updated["volumes"] = [_rewrite_volume_mount(item, ctx) for item in volumes]
    return updated


def _rename_service_keys(
    services: dict[str, Any], ctx: ComposeNamingContext
) -> dict[str, Any]:
    renamed: dict[str, Any] = {}
    for key, spec in services.items():
        physical_key = _map_logical_service_name(key, ctx)
        if physical_key in renamed:
            raise ValueError(f"duplicate compose service key after rename: {physical_key!r}")
        renamed[physical_key] = spec
    return renamed


def apply_compose_prefix(
    document: dict[str, Any], ctx: ComposeNamingContext
) -> dict[str, Any]:
    """Rewrite logical built-in service/volume names to physical names when prefix is active."""
    if not ctx.uses_prefix:
        return document

    services = document.get("services")
    if not isinstance(services, dict):
        return document

    rewritten_services = {
        name: _rewrite_service_spec(spec, ctx)
        for name, spec in services.items()
        if isinstance(spec, dict)
    }
    document["services"] = _rename_service_keys(rewritten_services, ctx)

    volumes = document.get("volumes")
    if isinstance(volumes, dict) and LOGICAL_POSTGRES_VOLUME in volumes:
        volumes[ctx.postgres_volume_name] = volumes.pop(LOGICAL_POSTGRES_VOLUME)

    if ctx.compose_project_name:
        document["name"] = ctx.compose_project_name

    return document


def _apply_legacy_postgres_service_rename(
    document: dict[str, Any], ctx: ComposeNamingContext
) -> dict[str, Any]:
    """4.6 ``POSTGRES_SERVICE_NAME`` rename without compose prefix."""
    if ctx.uses_prefix or ctx.postgres_service_name == LOGICAL_DB:
        return document

    services = document.get("services")
    if not isinstance(services, dict) or LOGICAL_DB not in services:
        return document

    legacy_ctx = ComposeNamingContext(
        compose_prefix=None,
        compose_project_name=None,
        postgres_service_name=ctx.postgres_service_name,
        odoo_service_name=LOGICAL_ODOO,
        postgres_volume_name=LOGICAL_POSTGRES_VOLUME,
    )
    rewritten_services = {
        name: _rewrite_service_spec(spec, legacy_ctx)
        for name, spec in services.items()
        if isinstance(spec, dict)
    }
    db_spec = rewritten_services.pop(LOGICAL_DB)
    rewritten_services[ctx.postgres_service_name] = db_spec
    document["services"] = rewritten_services
    return document


def apply_compose_physical_names(
    document: dict[str, Any],
    ctx: ComposeNamingContext,
    network_ctx=None,
) -> dict[str, Any]:
    """Apply prefix rewrite, legacy postgres rename, and optional network rewrite."""
    from .network_names import ComposeNetworkContext, apply_compose_network

    apply_compose_prefix(document, ctx)
    _apply_legacy_postgres_service_rename(document, ctx)
    if isinstance(network_ctx, ComposeNetworkContext) and network_ctx.is_active:
        apply_compose_network(document, network_ctx, ctx)
    return document
