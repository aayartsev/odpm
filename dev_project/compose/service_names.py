"""Compose logical vs physical service naming (4.7 prefix track)."""

from __future__ import annotations

import re
from dataclasses import dataclass

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
