"""Runtime config preview for plan evaluation and file diffs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from ..config.payload import runtime_config_path
from ..inside_docker_app.exceptions import ConfigValidationError

if TYPE_CHECKING:
    from ..config import Config

PLAN_ONLY_ARGUMENT_KEYS = frozenset(
    {"plan", "plan_no_docker", "plan_show_diff"},
)
_RUNTIME_PREVIEW_CACHE_KEY = "_odpm_plan_runtime_preview_cache"


def clear_runtime_config_preview_cache(config: Config) -> None:
    if hasattr(config, _RUNTIME_PREVIEW_CACHE_KEY):
        delattr(config, _RUNTIME_PREVIEW_CACHE_KEY)


def _runtime_preview_cache(config: Config) -> dict[str, str | None]:
    cache = getattr(config, _RUNTIME_PREVIEW_CACHE_KEY, None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(config, _RUNTIME_PREVIEW_CACHE_KEY, cache)
    return cache


def strip_plan_only_arguments(arguments: dict) -> dict:
    return {
        key: value
        for key, value in arguments.items()
        if key not in PLAN_ONLY_ARGUMENT_KEYS
    }


def format_runtime_config_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def runtime_config_payload_from_config(config: Config) -> dict:
    from ..container_config import ContainerConfig

    container = ContainerConfig.from_odpm_config(config)
    payload = container.to_dict()
    arguments = payload.get("arguments") or {}
    if isinstance(arguments, dict):
        payload["arguments"] = strip_plan_only_arguments(arguments)
    return payload


def normalize_runtime_config_text(raw_text: str) -> str:
    if not raw_text.strip():
        return ""
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ConfigValidationError("runtime config must be a JSON object")
    arguments = payload.get("arguments") or {}
    if isinstance(arguments, dict):
        payload["arguments"] = strip_plan_only_arguments(arguments)
    return format_runtime_config_payload(payload)


def prepare_runtime_config_for_compose_preview(config: Config) -> bool:
    """Populate runtime fields the same way compose.service execute would."""
    from dev_project import plan_compose_preview as compose_preview_shim

    try:
        with patch("dev_project.compose_service_builder.write_runtime_config"):
            compose_preview_shim.preview_compose_service(config)
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
        from dev_project import plan_runtime_preview as shim

        text = format_runtime_config_payload(
            shim.runtime_config_payload_from_config(config)
        )
    except (TypeError, ValueError, ConfigValidationError):
        cache["preview"] = None
        return None
    cache["preview"] = text
    return text


def normalized_runtime_config_text_from_disk(
    project_dir: str, *, config: Config | None = None
) -> str:
    if config is not None:
        cache = _runtime_preview_cache(config)
        if "on_disk" in cache:
            return cache["on_disk"] or ""
    path = runtime_config_path(project_dir)
    if not os.path.isfile(path):
        text = ""
    else:
        try:
            text = normalize_runtime_config_text(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, ConfigValidationError):
            text = ""
    if config is not None:
        _runtime_preview_cache(config)["on_disk"] = text
    return text
