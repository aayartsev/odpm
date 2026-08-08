"""Frozen build request for a CI image backend."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImageBuildSpec:
    context_dir: str
    dockerfile: str
    tag: str
    platform: str
    push: bool
    project_dir: str
