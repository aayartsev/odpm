"""File-level diffs for odpm --plan --plan-show-diff."""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from .. import constants, translations
from ..host.cli.args import OdpmCliArgs
from ..inside_docker_app.exceptions import ConfigValidationError
from .compose_preview import docker_compose_path, preview_compose_service
from .core import OdpmPlan
from .runtime_preview import (
    normalized_runtime_config_text_from_disk,
    preview_runtime_config_text,
)

if TYPE_CHECKING:
    from ..config import Config
    from ..project_env import CreateProjectEnvironment


@dataclass(frozen=True)
class PlanFileDiff:
    path: str
    unified_diff: str | None = None
    summary: str | None = None


def _step_would_change(plan: OdpmPlan, step_id: str) -> bool:
    for step in plan.steps:
        if step.id == step_id:
            return step.should_execute()
    return False


def _read_text(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    return Path(path).read_text(encoding="utf-8")


def _make_unified_diff(path: str, old_text: str, new_text: str) -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    if old_text and not old_text.endswith("\n"):
        old_lines[-1] += "\n"
    if new_text and not new_text.endswith("\n"):
        new_lines[-1] += "\n"
    return "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def diff_line_summary(unified_diff: str) -> str:
    adds = removes = 0
    for line in unified_diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            adds += 1
        elif line.startswith("-"):
            removes += 1
    return f"+{adds} -{removes} lines"


def _plan_file_diff(path: str, old_text: str, new_text: str) -> PlanFileDiff | None:
    if old_text == new_text:
        return None
    unified = _make_unified_diff(path, old_text, new_text)
    if not unified.strip():
        return None
    return PlanFileDiff(
        path=path,
        unified_diff=unified,
        summary=diff_line_summary(unified),
    )


def preview_dockerignore_content(config: Config) -> str:
    template_path = config.project_dockerignore_template_path
    content = Path(template_path).read_text(encoding="utf-8")
    return content.replace(
        translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
        translations.get_translation(translations.DO_NOT_CHANGE_FILE),
    )


def diff_runtime_config(config: Config) -> PlanFileDiff | None:
    preview = preview_runtime_config_text(config)
    if preview is None:
        return None
    on_disk = normalized_runtime_config_text_from_disk(
        config.project_dir,
        config=config,
    )
    return _plan_file_diff(constants.ODPM_RUNTIME_CONFIG_REL_PATH, on_disk, preview)


def diff_dockerignore(config: Config) -> PlanFileDiff | None:
    try:
        preview = preview_dockerignore_content(config)
    except OSError:
        return None
    on_disk = _read_text(os.path.join(config.project_dir, constants.DOCKERIGNORE))
    return _plan_file_diff(constants.DOCKERIGNORE, on_disk, preview)


def preview_docker_compose_content(
    config: Config, project_env: CreateProjectEnvironment
) -> str | None:
    mapped = getattr(project_env, "mapped_folders", None)
    if not isinstance(mapped, list) or not mapped:
        project_env.links.map_folders()
    try:
        preview_compose_service(config)
        return project_env.compose_generator.render_docker_compose_content()
    except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
        return None


def diff_docker_compose(
    config: Config, project_env: CreateProjectEnvironment | None
) -> PlanFileDiff | None:
    if project_env is None:
        return None
    preview = preview_docker_compose_content(config, project_env)
    if preview is None:
        return None
    on_disk = _read_text(docker_compose_path(config.project_dir))
    return _plan_file_diff("docker-compose.yml", on_disk, preview)


def diff_deps_lock_summary() -> PlanFileDiff:
    return PlanFileDiff(
        path=constants.DEPS_LOCK_REL_PATH,
        unified_diff=None,
        summary="will rewrite from resolved commits",
    )


def build_plan_diffs(
    plan: OdpmPlan,
    config: Config,
    args: OdpmCliArgs,
    project_env: CreateProjectEnvironment | None = None,
) -> tuple[PlanFileDiff, ...]:
    if not args.plan_show_diff:
        return ()
    diffs: list[PlanFileDiff] = []
    if _step_would_change(plan, "compose.service"):
        runtime_diff = diff_runtime_config(config)
        if runtime_diff is not None:
            diffs.append(runtime_diff)
    if _step_would_change(plan, "compose.generate"):
        with patch("dev_project.project_env.compose.Path.mkdir"):
            compose_diff = diff_docker_compose(config, project_env)
        if compose_diff is not None:
            diffs.append(compose_diff)
    if _step_would_change(plan, "template.dockerignore"):
        dockerignore_diff = diff_dockerignore(config)
        if dockerignore_diff is not None:
            diffs.append(dockerignore_diff)
    if _step_would_change(plan, "git.lock_collect"):
        diffs.append(diff_deps_lock_summary())
    return tuple(diffs)
