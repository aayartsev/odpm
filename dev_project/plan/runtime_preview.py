"""Runtime config preview for plan evaluation and file diffs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from ..config.payload import runtime_config_path
from ..inside_docker_app.exceptions import ConfigValidationError

if TYPE_CHECKING:
    from ..config import Config

PLAN_ONLY_ARGUMENT_KEYS = frozenset(
    {"plan", "plan_format", "plan_no_docker", "plan_show_diff", "plan_strict"},
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
    return json.dumps(payload, ensure_ascii=False, indent=4, sort_keys=True) + "\n"


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


def prepare_runtime_config_for_compose_preview(config: Config) -> bool:
    from .compose_preview import (
        prepare_runtime_config_for_compose_preview as prepare,
    )

    return prepare(config)


def preview_runtime_config_text(config: Config) -> str | None:
    from .compose_preview import preview_runtime_config_text as preview

    return preview(config)
