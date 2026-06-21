"""Read-only compose preview helpers for odpm --plan step evaluation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from .. import constants
from ..compose.service_builder import ComposeServiceBuilder
from ..compose.start_command import ComposeOdooService
from ..config.payload import runtime_config_path
from ..inside_docker_app.exceptions import ConfigValidationError
from .core import project_template_needs_upgrade, runtime_config_stale
from .runtime_preview import (
    format_runtime_config_payload,
    normalized_runtime_config_text_from_disk,
    runtime_config_payload_from_config,
    _runtime_preview_cache,
)

if TYPE_CHECKING:
    from ..config import Config
    from ..prepare.types import PrepareContext


def docker_compose_path(project_dir: str) -> str:
    return os.path.join(project_dir, "docker-compose.yml")


def preview_compose_service(config: Config):
    with patch("dev_project.config.payload.write_runtime_config"):
        return ComposeServiceBuilder(config).build()


def prepare_runtime_config_for_compose_preview(config: Config) -> bool:
    """Populate runtime fields the same way compose.service execute would."""
    try:
        preview_compose_service(config)
        return True
    except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
        try:
            config.generate_odoo_conf_docker_data()
            return True
        except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
            return False


def preview_runtime_config_text(config: Config) -> str | None:
    cache = _runtime_preview_cache(config)
    if "preview" in cache:
        return cache["preview"]
    if not prepare_runtime_config_for_compose_preview(config):
        cache["preview"] = None
        return None
    try:
        text = format_runtime_config_payload(
            runtime_config_payload_from_config(config)
        )
    except (TypeError, ValueError, ConfigValidationError):
        cache["preview"] = None
        return None
    cache["preview"] = text
    return text


def compose_start_command_changed(config: Config) -> bool:
    existing = getattr(config, "compose_service", None)
    if not isinstance(existing, ComposeOdooService):
        return False
    try:
        preview = preview_compose_service(config)
    except (AttributeError, TypeError, ValueError, ConfigValidationError):
        return True
    return preview.command != existing.command


def compose_service_needs_update(ctx: PrepareContext) -> tuple[bool, str]:
    config = ctx.config
    host = ctx.host_ctx
    if runtime_config_stale(config):
        return True, "venv_lock_hash changed"
    runtime_path = runtime_config_path(host.project_dir)
    if os.path.isfile(runtime_path):
        try:
            preview = preview_runtime_config_text(config)
            on_disk = normalized_runtime_config_text_from_disk(
                host.project_dir,
                config=config,
            )
            if preview is not None and preview != on_disk:
                return True, "runtime config payload changed"
        except (OSError, TypeError, ValueError, ConfigValidationError):
            pass
    if compose_start_command_changed(config):
        return True, "compose start command changed"
    return False, "runtime config and start command unchanged"


def _project_env_has_volume_map(ctx: PrepareContext) -> bool:
    mapped = getattr(ctx.links.env, "mapped_folders", None)
    return isinstance(mapped, list)


def compose_generate_needs_execute(ctx: PrepareContext) -> tuple[bool, str]:
    host = ctx.host_ctx
    if project_template_needs_upgrade(
        host.project_dir,
        constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        constants.COMPOSE_TEMPLATE_MARKERS,
    ):
        return True, "compose template stale"
    needs_service, service_reason = compose_service_needs_update(ctx)
    if needs_service:
        return True, service_reason
    compose_path = docker_compose_path(host.project_dir)
    if not os.path.isfile(compose_path):
        return True, "docker-compose.yml missing"
    if docker_compose_matches_preview(ctx):
        return False, "docker-compose.yml matches preview"
    if _project_env_has_volume_map(ctx):
        return True, "docker-compose.yml differs from preview"
    return False, "docker-compose.yml present; full preview needs volume map"


def docker_compose_matches_preview(ctx: PrepareContext) -> bool:
    host = ctx.host_ctx
    compose_path = docker_compose_path(host.project_dir)
    if not os.path.isfile(compose_path):
        return False
    if not _project_env_has_volume_map(ctx):
        return False
    try:
        preview_compose_service(ctx.config)
        preview = ctx.compose_generator.render_docker_compose_content()
    except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
        return False
    try:
        on_disk = Path(compose_path).read_text(encoding="utf-8")
    except OSError:
        return False
    return on_disk == preview


def vscode_settings_up_to_date(config: Config) -> bool:
    settings_path = os.path.join(config.project_dir, ".vscode", "settings.json")
    launch_path = os.path.join(config.project_dir, ".vscode", "launch.json")
    if not os.path.isfile(settings_path) or not os.path.isfile(launch_path):
        return False
    try:
        return str(config.python_version) in Path(settings_path).read_text(
            encoding="utf-8"
        )
    except OSError:
        return False
