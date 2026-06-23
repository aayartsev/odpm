"""File-level diffs for odpm --plan --plan-show-diff."""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from .. import constants
from ..translations import _
from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..inside_docker_app.exceptions import ConfigValidationError
from .compose_preview import docker_compose_path
from .debug_profile_preview import (
    normalized_debug_profile_text_from_disk,
    preview_debug_profile_text,
)
from .secrets_preview import secrets_needs_update, secrets_source_key_count
from .core import OdpmPlan
from .runtime_preview import normalized_runtime_config_text_from_disk

if TYPE_CHECKING:
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


def preview_dockerignore_content(host_ctx: HostProjectContext) -> str:
    template_path = host_ctx.docker_layout.project_dockerignore_template_path
    content = Path(template_path).read_text(encoding="utf-8")
    return content.replace(
        _('If you want drop this file to default values, just delete it'),
        _('Do not change this file, its content is generating automatically'),
    )


def diff_debug_profile(
    host_ctx: HostProjectContext, project_env: CreateProjectEnvironment | None
) -> PlanFileDiff | None:
    if project_env is None:
        return None
    preview = preview_debug_profile_text(project_env)
    if preview is None:
        return None
    on_disk = normalized_debug_profile_text_from_disk(host_ctx.project_dir)
    return _plan_file_diff(constants.ODPM_DEBUG_PROFILE_REL_PATH, on_disk, preview)


def diff_runtime_config_text(
    preview: str | None, on_disk: str
) -> PlanFileDiff | None:
    if preview is None:
        return None
    return _plan_file_diff(constants.ODPM_RUNTIME_CONFIG_REL_PATH, on_disk, preview)


def diff_dockerignore(host_ctx: HostProjectContext) -> PlanFileDiff | None:
    try:
        preview = preview_dockerignore_content(host_ctx)
    except OSError:
        return None
    on_disk = _read_text(os.path.join(host_ctx.project_dir, constants.DOCKERIGNORE))
    return _plan_file_diff(constants.DOCKERIGNORE, on_disk, preview)


def preview_docker_compose_content(
    project_env: CreateProjectEnvironment,
) -> str | None:
    mapped = getattr(project_env, "mapped_folders", None)
    if not isinstance(mapped, list) or not mapped:
        project_env.links.map_folders()
    try:
        project_env.plan_preview_compose_service()
        return project_env.compose_generator.render_docker_compose_content()
    except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
        return None


def diff_docker_compose_text(
    preview: str | None, project_dir: str
) -> PlanFileDiff | None:
    if preview is None:
        return None
    on_disk = _read_text(docker_compose_path(project_dir))
    return _plan_file_diff("docker-compose.yml", on_disk, preview)


def diff_deps_lock_summary() -> PlanFileDiff:
    return PlanFileDiff(
        path=constants.DEPS_LOCK_REL_PATH,
        unified_diff=None,
        summary="will rewrite from resolved commits",
    )


def diff_secrets_materialize_summary(project_dir: str) -> PlanFileDiff | None:
    needs_update, _reason = secrets_needs_update(project_dir)
    if not needs_update:
        return None
    key_count = secrets_source_key_count(project_dir)
    if key_count:
        summary = (
            f"will materialize {key_count} secret keys from .odpm/secrets.json"
        )
    else:
        summary = "will remove stale .odpm/runtime/secrets.json"
    return PlanFileDiff(
        path=constants.ODPM_SECRETS_RUNTIME_REL_PATH,
        unified_diff=None,
        summary=summary,
    )


def _runtime_config_preview_text(
    project_env: CreateProjectEnvironment | None,
) -> str | None:
    if project_env is None:
        return None
    return project_env.plan_runtime_config_preview_text()


def _runtime_config_on_disk_text(
    host_ctx: HostProjectContext,
    project_env: CreateProjectEnvironment | None,
) -> str:
    if project_env is None:
        return ""
    return normalized_runtime_config_text_from_disk(
        host_ctx.project_dir,
        config=project_env.runtime_preview_cache_config(),
    )


def build_plan_diffs(
    plan: OdpmPlan,
    host_ctx: HostProjectContext,
    args: OdpmCliArgs,
    project_env: CreateProjectEnvironment | None = None,
) -> tuple[PlanFileDiff, ...]:
    if not args.plan_show_diff:
        return ()
    diffs: list[PlanFileDiff] = []
    if _step_would_change(plan, "ide.debug_profile"):
        debug_profile_diff = diff_debug_profile(host_ctx, project_env)
        if debug_profile_diff is not None:
            diffs.append(debug_profile_diff)
    if _step_would_change(plan, "secrets.materialize"):
        secrets_diff = diff_secrets_materialize_summary(host_ctx.project_dir)
        if secrets_diff is not None:
            diffs.append(secrets_diff)
    if _step_would_change(plan, "compose.service"):
        runtime_diff = diff_runtime_config_text(
            _runtime_config_preview_text(project_env),
            _runtime_config_on_disk_text(host_ctx, project_env),
        )
        if runtime_diff is not None:
            diffs.append(runtime_diff)
    if _step_would_change(plan, "compose.generate"):
        compose_preview = None
        if project_env is not None:
            with patch("pathlib.Path.mkdir"):
                compose_preview = preview_docker_compose_content(project_env)
        compose_diff = diff_docker_compose_text(compose_preview, host_ctx.project_dir)
        if compose_diff is not None:
            diffs.append(compose_diff)
    if _step_would_change(plan, "template.dockerignore"):
        dockerignore_diff = diff_dockerignore(host_ctx)
        if dockerignore_diff is not None:
            diffs.append(dockerignore_diff)
    if _step_would_change(plan, "git.lock_collect"):
        diffs.append(diff_deps_lock_summary())
    return tuple(diffs)
