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
from .core import project_template_needs_upgrade, runtime_config_stale_for_project
from .runtime_preview import (
    format_runtime_config_payload,
    normalized_runtime_config_text_from_disk,
    runtime_config_payload_from_bootstrap,
    _runtime_preview_cache,
    _RUNTIME_PREVIEW_CACHE_KEY,
)

if TYPE_CHECKING:
    from ..host.context import HostProjectContext
    from ..host.ports import BootstrapHandle
    from ..prepare.types import PrepareContext


def compose_preview_mutable_snapshot(
    bootstrap: BootstrapHandle,
) -> tuple[object, object, object]:
    """Capture compose-preview mutable fields on *bootstrap* for later restore."""
    return (
        bootstrap.runtime.compose_service,
        bootstrap.runtime.container_run_mode,
        getattr(bootstrap, _RUNTIME_PREVIEW_CACHE_KEY, None),
    )


def restore_compose_preview_mutable_snapshot(
    bootstrap: BootstrapHandle, snapshot: tuple[object, object, object]
) -> None:
    """Restore fields saved by :func:`compose_preview_mutable_snapshot`."""
    compose_service, container_run_mode, cache = snapshot
    bootstrap.runtime.compose_service = compose_service
    bootstrap.runtime.container_run_mode = container_run_mode
    if cache is None:
        if hasattr(bootstrap, _RUNTIME_PREVIEW_CACHE_KEY):
            delattr(bootstrap, _RUNTIME_PREVIEW_CACHE_KEY)
    else:
        setattr(bootstrap, _RUNTIME_PREVIEW_CACHE_KEY, cache)


def docker_compose_path(project_dir: str) -> str:
    return os.path.join(project_dir, "docker-compose.yml")


def preview_compose_service(bootstrap: BootstrapHandle):
    with patch("dev_project.compose.service_builder.persist_runtime_config"):
        return ComposeServiceBuilder(bootstrap).build()


def prepare_runtime_config_for_compose_preview(bootstrap: BootstrapHandle) -> bool:
    """Populate runtime fields the same way compose.service execute would."""
    try:
        preview_compose_service(bootstrap)
        return True
    except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
        try:
            bootstrap.generate_odoo_conf_docker_data()
            return True
        except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
            return False


def preview_runtime_config_text(bootstrap: BootstrapHandle) -> str | None:
    cache = _runtime_preview_cache(bootstrap)
    if "preview" in cache:
        return cache["preview"]
    if not prepare_runtime_config_for_compose_preview(bootstrap):
        cache["preview"] = None
        return None
    try:
        text = format_runtime_config_payload(
            runtime_config_payload_from_bootstrap(bootstrap)
        )
    except (TypeError, ValueError, ConfigValidationError):
        cache["preview"] = None
        return None
    cache["preview"] = text
    return text


def compose_start_command_changed(bootstrap: BootstrapHandle) -> bool:
    existing = bootstrap.runtime.compose_service
    if not isinstance(existing, ComposeOdooService):
        return False
    try:
        preview = preview_compose_service(bootstrap)
    except (AttributeError, TypeError, ValueError, ConfigValidationError):
        return True
    return preview.command != existing.command


def compose_service_needs_update(ctx: PrepareContext) -> tuple[bool, str]:
    def _evaluate(bootstrap: BootstrapHandle) -> tuple[bool, str]:
        host = ctx.host_ctx
        if runtime_config_stale_for_project(
            host.project_dir,
            ctx.compute_venv_lock_hash(),
        ):
            return True, "venv_lock_hash changed"
        if ctx.compose_preview.compose_start_command_changed():
            return True, "compose start command changed"
        runtime_path = runtime_config_path(host.project_dir)
        if os.path.isfile(runtime_path):
            try:
                preview = ctx.compose_preview.runtime_config_text()
                on_disk = normalized_runtime_config_text_from_disk(
                    host.project_dir,
                    bootstrap=bootstrap,
                )
                if preview is not None and preview != on_disk:
                    return True, "runtime config payload changed"
            except (OSError, TypeError, ValueError, ConfigValidationError):
                pass
        return False, "runtime config and start command unchanged"

    return ctx.compose_preview.run_with_mutable_snapshot(_evaluate)


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

    def _evaluate(bootstrap: BootstrapHandle) -> str:
        bootstrap.ensure_docker_capabilities()
        ctx.compose_preview.preview_compose_service()
        return ctx.compose_generator.render_docker_compose_content()

    try:
        preview = ctx.compose_preview.run_with_mutable_snapshot(_evaluate)
    except (AttributeError, OSError, TypeError, ValueError, ConfigValidationError):
        return False
    try:
        on_disk = Path(compose_path).read_text(encoding="utf-8")
    except OSError:
        return False
    return on_disk == preview


def vscode_settings_up_to_date(host_ctx: HostProjectContext) -> bool:
    settings_path = os.path.join(host_ctx.project_dir, ".vscode", "settings.json")
    launch_path = os.path.join(host_ctx.project_dir, ".vscode", "launch.json")
    if not os.path.isfile(settings_path) or not os.path.isfile(launch_path):
        return False
    try:
        return str(host_ctx.project_settings.python_version) in Path(settings_path).read_text(
            encoding="utf-8"
        )
    except OSError:
        return False
