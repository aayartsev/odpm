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
from .git.deps_lock import deps_lock_path, load_deps_lock
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
        ctx = HostProjectContext.from_config(config, arguments=args)
        steps: list[PlanStep] = []
        warnings: list[str] = []

        if ctx.update_lock and ctx.skip_git_update:
            warnings.append(
                "--update-lock cannot be used together with --no-git-update"
            )

        if ctx.update_lock:
            steps.append(
                PlanStep(
                    "git.update_lock",
                    "Resolve git repos and write .odpm/deps.lock.json",
                    required=True,
                )
            )
        elif ctx.skip_git_update:
            steps.append(
                PlanStep(
                    "git.ensure_present",
                    "Verify local platform and developing git directories exist",
                    required=True,
                )
            )
        else:
            steps.append(
                PlanStep(
                    "git.materialize",
                    "Clone or update platform, developing, and dependency git repos",
                    required=True,
                )
            )
            if deps_lock_file_exists(config.project_dir):
                steps.append(
                    PlanStep(
                        "git.lock_apply",
                        "Apply pinned commits from .odpm/deps.lock.json before checkout",
                        required=True,
                    )
                )

        steps.append(
            PlanStep(
                "project.map_folders",
                "Build docker volume mapping for Odoo, venv, and addons",
                required=True,
            )
        )

        if project_template_needs_upgrade(
            config.project_dir,
            dockerfile_template_relative(config),
            constants.DOCKERFILE_TEMPLATE_MARKERS,
        ) or not base_image_identity_matches(config):
            steps.append(
                PlanStep(
                    "template.dockerfile",
                    "Regenerate project Dockerfile from odpm template",
                    required=True,
                )
            )

        if project_template_needs_upgrade(
            config.project_dir,
            constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
            constants.DOCKERIGNORE_TEMPLATE_MARKERS,
        ):
            steps.append(
                PlanStep(
                    "template.dockerignore",
                    "Regenerate root .dockerignore from .odpm/dockerignore",
                    required=True,
                )
            )

        steps.append(
            PlanStep(
                "docker.engine.check",
                "Check Docker engine and running odpm containers",
                required=config.check_system,
            )
        )

        if project_template_needs_upgrade(
            config.project_dir,
            constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
            constants.ODOO_CONFIG_TEMPLATE_MARKERS,
        ):
            steps.append(
                PlanStep(
                    "template.odoo_conf",
                    "Regenerate .odpm/dev_odoo_docker_config_file.conf template",
                    required=True,
                )
            )

        if runtime_config_stale(config):
            steps.append(
                PlanStep(
                    "venv.runtime_config",
                    "Write .odpm/runtime/config.json (venv lock hash / scenario payload)",
                    required=True,
                )
            )

        if project_template_needs_upgrade(
            config.project_dir,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
            constants.COMPOSE_TEMPLATE_MARKERS,
        ):
            steps.append(
                PlanStep(
                    "compose.template",
                    "Upgrade .odpm/docker-compose.yml project template",
                    required=True,
                )
            )

        steps.append(
            PlanStep(
                "compose.service",
                "Build compose start command and runtime config references",
                required=True,
            )
        )
        steps.append(
            PlanStep(
                "compose.generate",
                "Render docker-compose.yml from project template",
                required=True,
            )
        )
        steps.append(
            PlanStep(
                "compose.validate",
                "Validate generated docker-compose.yml",
                required=True,
            )
        )

        if not ctx.skip_git_update and not ctx.update_lock:
            steps.append(
                PlanStep(
                    "git.checkout",
                    "Checkout dependency repos to odoo version branch",
                    required=True,
                )
            )
            if deps_lock_file_exists(config.project_dir):
                lock = None
                try:
                    lock = load_deps_lock(deps_lock_path(config.project_dir))
                except ValueError:
                    warnings.append(
                        "Invalid .odpm/deps.lock.json; lock verify step omitted from plan"
                    )
                if lock is not None:
                    steps.append(
                        PlanStep(
                            "git.lock_verify",
                            "Verify checked-out commits match deps.lock.json",
                            required=config.policy.is_ci(),
                        )
                    )

        steps.append(
            PlanStep(
                "project.update_links",
                "Refresh module symlinks for developing project addons",
                required=config.create_module_links,
            )
        )

        if getattr(args, "build_image", False):
            steps.append(
                PlanStep(
                    "ci.build_image",
                    "Build CI Docker image from prepared context",
                    required=True,
                )
            )

        if not config.policy.skip_vscode:
            steps.append(
                PlanStep(
                    "vscode.settings",
                    "Update VS Code launch and workspace settings",
                    required=False,
                )
            )

        if (
            not getattr(args, "skip_start", False)
            and not ctx.update_lock
            and not getattr(args, "build_image", False)
        ):
            steps.append(
                PlanStep(
                    "compose.up",
                    "Run docker compose up (may add --force-recreate if stack is unhealthy)",
                    required=True,
                )
            )
            warnings.append(
                "Compose stack health is checked at runtime; unhealthy stacks get --force-recreate"
            )

        return OdpmPlan(steps=tuple(steps), warnings=tuple(warnings))


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
