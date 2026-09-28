"""Compose scenario defaults with security profile conflict rules.

Source of truth for scenario → security profile presets and for rules that
cross the scenario / security axes (CI bind topology, password bootstrap).
"""

from __future__ import annotations

from . import constants
from .security_profiles import (
    SECURITY_PROFILE_CONVENIENCE,
    SECURITY_PROFILE_HARDENED,
    SecurityProfile,
    binds_for_security_profile,
)

PRESETS: dict[str, SecurityProfile] = {
    constants.DEVELOPER_SCENARIO: SECURITY_PROFILE_CONVENIENCE,
    constants.SERVER_SCENARIO: SECURITY_PROFILE_HARDENED,
    constants.CI_SCENARIO: SECURITY_PROFILE_CONVENIENCE,
}


def security_profile_for_scenario(scenario: str) -> SecurityProfile:
    return PRESETS.get(scenario, SECURITY_PROFILE_CONVENIENCE)


def resolve_security_profile(
    scenario: str,
    *,
    override: SecurityProfile | None = None,
) -> SecurityProfile:
    """Effective profile: explicit override wins over scenario default."""
    if override is not None:
        return override
    return security_profile_for_scenario(scenario)


def effective_binds(
    scenario: str,
    profile: SecurityProfile,
) -> tuple[bool, bool]:
    """Return ``(bind_postgres_localhost, bind_published_ports_localhost)``.

    CI port topology is scenario-owned regardless of profile override.
    """
    if scenario == constants.CI_SCENARIO:
        return True, False
    return binds_for_security_profile(profile)


def password_bootstrap_enabled(
    scenario: str,
    profile: SecurityProfile,
) -> bool:
    """True when hardened file-provider bootstrap of Odoo password secrets applies."""
    if scenario == constants.CI_SCENARIO:
        return False
    return profile == SECURITY_PROFILE_HARDENED
