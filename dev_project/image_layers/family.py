"""Layer family labels for registry tags (docs convention, ADR-027)."""

from __future__ import annotations

FAMILY_DEV = "dev"
FAMILY_RUNTIME = "runtime"

_PROFILE_TO_FAMILY = {
    "full": FAMILY_DEV,
    "medium": FAMILY_RUNTIME,
}


def family_for_profile(profile: str) -> str:
    """Map ADR-007 base profile to family tag segment.

    Profile ``ci`` is not a target product family; fall back to the profile
    name so tags remain unique without inventing a family label.
    """
    key = (profile or "").strip().lower()
    return _PROFILE_TO_FAMILY.get(key, key or "unknown")
