"""Backward-compatible shim for ``dev_project.plan.diff``."""

from dev_project.plan.diff import (
    PlanFileDiff,
    build_plan_diffs,
    diff_docker_compose,
    diff_dockerignore,
    diff_deps_lock_summary,
    diff_line_summary,
    diff_runtime_config,
    preview_docker_compose_content,
    preview_dockerignore_content,
)
from dev_project.plan.runtime_preview import (
    normalized_runtime_config_text_from_disk,
    preview_runtime_config_text,
)

__all__ = [
    "PlanFileDiff",
    "build_plan_diffs",
    "diff_docker_compose",
    "diff_dockerignore",
    "diff_deps_lock_summary",
    "diff_line_summary",
    "diff_runtime_config",
    "normalized_runtime_config_text_from_disk",
    "preview_docker_compose_content",
    "preview_dockerignore_content",
    "preview_runtime_config_text",
]
