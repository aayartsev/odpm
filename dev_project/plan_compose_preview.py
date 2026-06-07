"""Backward-compatible shim for ``dev_project.plan.compose_preview``."""

from dev_project.plan.compose_preview import (
    compose_generate_needs_execute,
    compose_service_needs_update,
    compose_start_command_changed,
    docker_compose_matches_preview,
    docker_compose_path,
    normalized_runtime_config_text_from_disk,
    preview_compose_service,
    preview_runtime_config_text,
    vscode_settings_up_to_date,
)

__all__ = [
    "compose_generate_needs_execute",
    "compose_service_needs_update",
    "compose_start_command_changed",
    "docker_compose_matches_preview",
    "docker_compose_path",
    "normalized_runtime_config_text_from_disk",
    "preview_compose_service",
    "preview_runtime_config_text",
    "vscode_settings_up_to_date",
]
