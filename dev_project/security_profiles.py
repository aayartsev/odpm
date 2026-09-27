"""Security profile axis (convenience / hardened) — passwords and publish binds."""

from __future__ import annotations

from typing import Literal

from . import constants
from .logging import get_module_logger
from .translations import _

_logger = get_module_logger(__name__)

SecurityProfile = Literal["convenience", "hardened"]

SECURITY_PROFILE_CONVENIENCE: SecurityProfile = "convenience"
SECURITY_PROFILE_HARDENED: SecurityProfile = "hardened"
SECURITY_PROFILE_VALUES: frozenset[str] = frozenset(
    {SECURITY_PROFILE_CONVENIENCE, SECURITY_PROFILE_HARDENED}
)

ODPM_SECRET_KEY_DB_MANAGER_PASSWORD = "odpm.db_manager_password"
ODPM_SECRET_KEY_DB_DEFAULT_ADMIN_PASSWORD = "odpm.db_default_admin_password"

ODOO_PASSWORD_SECRET_KEYS: tuple[str, ...] = (
    ODPM_SECRET_KEY_DB_MANAGER_PASSWORD,
    ODPM_SECRET_KEY_DB_DEFAULT_ADMIN_PASSWORD,
)

HARDENED_DB_MANAGER_PASSWORD_REF = (
    f"${{@secret:{ODPM_SECRET_KEY_DB_MANAGER_PASSWORD}}}"
)
HARDENED_DB_DEFAULT_ADMIN_PASSWORD_REF = (
    f"${{@secret:{ODPM_SECRET_KEY_DB_DEFAULT_ADMIN_PASSWORD}}}"
)


def security_profile_for_scenario(scenario: str) -> SecurityProfile:
    from . import policy_compose

    return policy_compose.security_profile_for_scenario(scenario)


def parse_security_profile(raw: str | None) -> SecurityProfile | None:
    """Return a valid profile override, or ``None`` when unset/invalid."""
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if value not in SECURITY_PROFILE_VALUES:
        _logger.warning(
            _(
                "Invalid {ENV}={VALUE!r} (use {ALLOWED}); using scenario default profile"
            ).format(
                ENV=constants.ODPM_SECURITY_PROFILE_ENV,
                VALUE=raw,
                ALLOWED=", ".join(sorted(SECURITY_PROFILE_VALUES)),
            ),
        )
        return None
    return value  # type: ignore[return-value]


def resolve_security_profile(
    scenario: str,
    *,
    override: SecurityProfile | None = None,
) -> SecurityProfile:
    """Effective profile: explicit override wins over scenario default."""
    from . import policy_compose

    return policy_compose.resolve_security_profile(scenario, override=override)


def binds_for_security_profile(
    profile: SecurityProfile,
) -> tuple[bool, bool]:
    """Return ``(bind_postgres_localhost, bind_published_ports_localhost)``."""
    if profile == SECURITY_PROFILE_HARDENED:
        return True, True
    return False, False
