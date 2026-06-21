"""Map RELEASE_VERSION to Debian/RPM native package version fields."""

from __future__ import annotations

import re

_RELEASE_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:-(.+))?$")


def parse_release_version(release_version: str) -> tuple[str, str | None]:
    """Split user-facing release into base semver and optional pre-release suffix."""
    match = _RELEASE_RE.fullmatch(release_version.strip())
    if not match:
        raise ValueError(f"Invalid RELEASE_VERSION: {release_version!r}")
    return match.group(1), match.group(2)


def debian_upstream_version(release_version: str) -> str:
    """Debian upstream version (``~`` separates pre-release from stable)."""
    base, suffix = parse_release_version(release_version)
    if suffix:
        return f"{base}~{suffix}"
    return base


def rpm_version_and_release(release_version: str) -> tuple[str, str]:
    """RPM ``Version`` (numeric) and ``Release`` (pre-release label or ``1``)."""
    base, suffix = parse_release_version(release_version)
    return base, suffix or "1"
