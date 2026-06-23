"""Scenario base Dockerfile profile selection (full / medium / ci)."""

from __future__ import annotations

import os
from typing import Literal

BaseImageProfile = Literal["full", "medium", "ci"]

_PROFILE_BY_SCENARIO = {
    "developer": "full",
    "server": "medium",
    "ci": "ci",
}


def base_image_profile_for_scenario(scenario: str) -> BaseImageProfile:
    return _PROFILE_BY_SCENARIO.get(scenario, "full")  # type: ignore[return-value]


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
