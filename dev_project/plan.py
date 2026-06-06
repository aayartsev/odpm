"""Dry-run plan for ``odpm --plan``: predict prepare/runtime steps without side effects."""

from __future__ import annotations

import json
import os
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from . import constants
from .config.payload import runtime_config_path
from .host_context import HostProjectContext
from .project_dir_manager import template_needs_upgrade
from .project_env.base_image_identity import base_image_identity_matches

if TYPE_CHECKING:
    from .config import Config


@dataclass(frozen=True)
class PlanStep:
    id: str
    action: str
    required: bool


@dataclass(frozen=True)
class OdpmPlan:
    steps: tuple[PlanStep, ...]
    warnings: tuple[str, ...] = ()


def skip_git_update(arguments: Namespace) -> bool:
    return bool(getattr(arguments, "no_git_update", False))


def update_lock_requested(arguments: Namespace) -> bool:
    return bool(getattr(arguments, "update_lock", False))


def deps_lock_file_exists(project_dir: str) -> bool:
    from .git.deps_lock import deps_lock_path

    return os.path.isfile(deps_lock_path(project_dir))


def project_template_needs_upgrade(
    project_dir: str, relative_path: str, markers: list[str]
) -> bool:
    path = os.path.join(project_dir, relative_path)
    if not os.path.exists(path):
        return True
    return template_needs_upgrade(path, markers)


def runtime_config_stale(config: Config) -> bool:
    path = runtime_config_path(config.project_dir)
    if not os.path.isfile(path):
        return True
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return True
    return payload.get("venv_lock_hash") != config.compute_venv_lock_hash()


def dockerfile_template_relative(config: Config) -> str:
    return os.path.join(
        constants.PROJECT_SERVICE_DIRECTORY,
        config.dockerfile_template_name,
    )


class OdpmPlanner:
    @classmethod
    def build(cls, config: Config, args: Namespace) -> OdpmPlan:
        from .prepare_registry import build_plan

        return build_plan(config, args)


def format_plan(plan: OdpmPlan) -> str:
    lines = ["ID                     Required  Action", "-" * 72]
    for step in plan.steps:
        flag = "yes" if step.required else "no"
        lines.append(f"{step.id:<22} {flag:<8}  {step.action}")
    if plan.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)
