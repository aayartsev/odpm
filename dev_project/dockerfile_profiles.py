"""Scenario base Dockerfile profile selection (full / medium / ci)."""

from __future__ import annotations

import os
from typing import Literal

from . import constants
from .logging import get_module_logger
from .translations import _

_logger = get_module_logger(__name__)

BaseImageProfile = Literal["full", "medium", "ci"]

BASE_IMAGE_PROFILE_VALUES: frozenset[str] = frozenset({"full", "medium", "ci"})

_PROFILE_BY_SCENARIO: dict[str, BaseImageProfile] = {
    "developer": "full",
    "server": "medium",
    "ci": "ci",
}


def base_image_profile_for_scenario(scenario: str) -> BaseImageProfile:
    return _PROFILE_BY_SCENARIO.get(scenario, "full")


def parse_base_image_profile(raw: str | None) -> BaseImageProfile | None:
    """Return a valid profile override, or ``None`` when unset/invalid."""
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if value not in BASE_IMAGE_PROFILE_VALUES:
        _logger.warning(
            _(
                "Invalid {ENV}={VALUE!r} (use {ALLOWED}); using scenario default profile"
            ).format(
                ENV=constants.ODPM_BASE_IMAGE_PROFILE_ENV,
                VALUE=raw,
                ALLOWED=", ".join(sorted(BASE_IMAGE_PROFILE_VALUES)),
            ),
        )
        return None
    return value  # type: ignore[return-value]


def resolve_base_image_profile(
    scenario: str,
    *,
    override: BaseImageProfile | None = None,
) -> BaseImageProfile:
    """Effective profile: explicit override wins over scenario default."""
    if override is not None:
        return override
    return base_image_profile_for_scenario(scenario)


def dockerfile_template_stem(distro_name: str, distro_version: str) -> str:
    return f"{distro_name}_{distro_version.replace('.', '')}_dockerfile"


def resolve_dockerfile_template_name(
    program_dir: str,
    distro_name: str,
    distro_version: str,
    profile: BaseImageProfile,
) -> str:
    """Return program template basename, preferring ``{stem}_{profile}`` when present."""
    stem = dockerfile_template_stem(distro_name, distro_version)
    profiled = f"{stem}_{profile}"
    templates_dir = os.path.join(program_dir, "dev_project", "templates")
    if os.path.isfile(os.path.join(templates_dir, profiled)):
        return profiled
    legacy = os.path.join(templates_dir, stem)
    if os.path.isfile(legacy):
        return stem
    return profiled
