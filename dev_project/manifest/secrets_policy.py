"""Manifest secrets requirements and host-side validation (4.7)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import ConfigError
from ..project_env.secrets import (
    parse_secrets_payload,
    read_secrets_source,
    secrets_example_path,
)
from ..translations import _

_PLACEHOLDER_VALUES = frozenset({"REPLACE_ME", "CHANGEME", "TODO"})


def is_secret_placeholder(value: str) -> bool:
    """True when a secrets.json value is still a template stub."""
    return value.strip() in _PLACEHOLDER_VALUES


@dataclass(frozen=True)
class ManifestSecretsSpec:
    """Effective secrets contract from manifest root + scenario overlay."""

    required: bool = False
    keys: tuple[str, ...] = ()


def secrets_spec_from_raw(value: Any) -> ManifestSecretsSpec | None:
    if not isinstance(value, dict) or not value:
        return None
    keys_raw = value.get("keys")
    keys: tuple[str, ...] = ()
    if isinstance(keys_raw, list):
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in keys_raw:
            key = str(item).strip()
            if key and key not in seen:
                seen.add(key)
                cleaned.append(key)
        keys = tuple(cleaned)
    required = bool(value.get("required", False))
    if not required and not keys:
        return None
    return ManifestSecretsSpec(required=required, keys=keys)


def merge_secrets_spec(base_raw: Any, overlay_raw: Any) -> ManifestSecretsSpec | None:
    base = secrets_spec_from_raw(base_raw)
    overlay = secrets_spec_from_raw(overlay_raw)
    if base is None and overlay is None:
        if not isinstance(overlay_raw, dict) or "required" not in overlay_raw:
            if not isinstance(base_raw, dict) or "required" not in base_raw:
                return None
    if isinstance(overlay_raw, dict) and "required" in overlay_raw:
        required = bool(overlay_raw.get("required", False))
    elif base is not None:
        required = base.required
    else:
        required = False

    merged_keys: list[str] = []
    seen: set[str] = set()
    for source in (base.keys if base else ()), (overlay.keys if overlay else ()):
        for key in source:
            if key not in seen:
                seen.add(key)
                merged_keys.append(key)

    if not required and not merged_keys:
        return None
    return ManifestSecretsSpec(required=required, keys=tuple(merged_keys))


def read_secrets_example_keys(project_dir: str) -> tuple[str, ...]:
    """Example key names for user-facing hints only (not a validation contract)."""
    path = secrets_example_path(project_dir)
    if not os.path.isfile(path):
        return ()
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        secrets = parse_secrets_payload(raw)
    except (OSError, json.JSONDecodeError, ConfigError):
        return ()
    return tuple(sorted(secrets))


def _secret_value_unset(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    upper = stripped.upper()
    return upper in _PLACEHOLDER_VALUES or upper == "REPLACE_ME"


def _missing_secrets_message(
    scenario: str,
    *,
    manifest_keys: tuple[str, ...] = (),
    example_keys: tuple[str, ...] = (),
) -> str:
    keys = manifest_keys or example_keys
    if keys:
        return _(
            "Scenario {SCENARIO} requires .odpm/secrets.json with keys: {KEYS}; "
            "copy from .odpm/secrets.example.json or pass --secrets-file"
        ).format(SCENARIO=scenario, KEYS=", ".join(keys))
    return _(
        "Scenario {SCENARIO} requires .odpm/secrets.json; "
        "copy from .odpm/secrets.example.json or pass --secrets-file"
    ).format(SCENARIO=scenario)


def collect_secrets_requirement_issues(
    project_dir: str,
    spec: ManifestSecretsSpec | None,
    *,
    mount_secrets_from_host: bool,
    scenario: str,
) -> list[str]:
    if not isinstance(spec, ManifestSecretsSpec) or not spec.required:
        return []

    if not mount_secrets_from_host:
        return []

    secrets = read_secrets_source(project_dir)
    if secrets is None:
        return [
            _missing_secrets_message(
                scenario,
                manifest_keys=spec.keys,
                example_keys=() if spec.keys else read_secrets_example_keys(project_dir),
            )
        ]

    if not spec.keys:
        return []

    missing = [key for key in spec.keys if key not in secrets]
    if missing:
        return [
            _(
                ".odpm/secrets.json is missing required keys: {KEYS}"
            ).format(KEYS=", ".join(missing))
        ]

    unset = [
        key
        for key in spec.keys
        if key in secrets and _secret_value_unset(secrets[key])
    ]
    if unset:
        return [
            _(
                ".odpm/secrets.json has placeholder values for keys: {KEYS}"
            ).format(KEYS=", ".join(unset))
        ]
    return []


def ensure_secrets_requirements_met(
    project_dir: str,
    spec: ManifestSecretsSpec | None,
    *,
    mount_secrets_from_host: bool,
    scenario: str,
) -> None:
    issues = collect_secrets_requirement_issues(
        project_dir,
        spec,
        mount_secrets_from_host=mount_secrets_from_host,
        scenario=scenario,
    )
    if not issues:
        return
    raise ConfigError(" ".join(issues))
