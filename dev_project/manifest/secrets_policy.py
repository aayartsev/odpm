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
class ManifestSecretsProviderConfig:
    """Manifest ``secrets.provider`` object (type + Infisical fields)."""

    type: str
    host: str | None = None
    project_id: str | None = None
    project_slug: str | None = None
    environment_slug: str | None = None
    secret_path: str = "/"
    recursive: bool = False
    key_map: tuple[tuple[str, str], ...] = ()

    def as_mapping(self) -> dict[str, Any]:
        mapping: dict[str, Any] = {"type": self.type}
        if self.host:
            mapping["host"] = self.host
        if self.project_id:
            mapping["project_id"] = self.project_id
        if self.project_slug:
            mapping["project_slug"] = self.project_slug
        if self.environment_slug:
            mapping["environment_slug"] = self.environment_slug
        mapping["secret_path"] = self.secret_path
        mapping["recursive"] = self.recursive
        if self.key_map:
            mapping["key_map"] = {src: dest for src, dest in self.key_map}
        return mapping


def parse_secrets_provider(value: Any) -> ManifestSecretsProviderConfig | None:
    if not isinstance(value, dict):
        return None
    type_name = str(value.get("type") or "").strip()
    if not type_name:
        return None
    key_map_raw = value.get("key_map") or {}
    key_map: list[tuple[str, str]] = []
    if isinstance(key_map_raw, dict):
        for source_key, dest_key in key_map_raw.items():
            src = str(source_key).strip()
            dest = str(dest_key).strip()
            if src and dest:
                key_map.append((src, dest))
    secret_path = str(value.get("secret_path") or "/").strip() or "/"
    return ManifestSecretsProviderConfig(
        type=type_name,
        host=str(value["host"]).strip() if value.get("host") else None,
        project_id=str(value["project_id"]).strip() if value.get("project_id") else None,
        project_slug=(
            str(value["project_slug"]).strip() if value.get("project_slug") else None
        ),
        environment_slug=(
            str(value["environment_slug"]).strip()
            if value.get("environment_slug")
            else None
        ),
        secret_path=secret_path,
        recursive=bool(value.get("recursive", False)),
        key_map=tuple(key_map),
    )


@dataclass(frozen=True)
class ManifestSecretsSpec:
    """Effective secrets contract from manifest root + scenario overlay."""

    required: bool = False
    keys: tuple[str, ...] = ()
    provider: ManifestSecretsProviderConfig | None = None


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
    provider = parse_secrets_provider(value.get("provider"))
    if not required and not keys and provider is None:
        return None
    return ManifestSecretsSpec(required=required, keys=keys, provider=provider)


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

    if isinstance(overlay_raw, dict) and "provider" in overlay_raw:
        provider = parse_secrets_provider(overlay_raw.get("provider"))
    elif overlay is not None and overlay.provider is not None:
        provider = overlay.provider
    elif base is not None:
        provider = base.provider
    else:
        provider = None

    if not required and not merged_keys and provider is None:
        return None
    return ManifestSecretsSpec(
        required=required,
        keys=tuple(merged_keys),
        provider=provider,
    )


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
