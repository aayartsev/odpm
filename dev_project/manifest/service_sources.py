"""Manifest ``service_sources``: named git links for sidecar build contexts."""

from __future__ import annotations

import re
from typing import Any

from ..errors import ConfigError
from ..translations import _

_SERVICE_SOURCE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def normalize_service_sources(value: Any) -> dict[str, str] | None:
    """Parse and validate ``service_sources`` object from manifest JSON."""
    if value is None:
        return None
    if not isinstance(value, dict) or not value:
        return None
    result: dict[str, str] = {}
    for key, raw in value.items():
        name = str(key).strip()
        if not _SERVICE_SOURCE_NAME_RE.match(name):
            raise ConfigError(
                _(
                    "service_sources key {NAME!r} is invalid; "
                    "use lowercase letters, digits, and underscores "
                    "(must start with a letter)."
                ).format(NAME=name)
            )
        link = str(raw).strip()
        if not link:
            raise ConfigError(
                _("service_sources.{NAME} must be a non-empty git link.").format(
                    NAME=name
                )
            )
        result[name] = link
    return result or None


def validate_service_source_fields(
    services: dict[str, Any] | None,
    *,
    service_sources: dict[str, str] | None,
) -> None:
    """Ensure ``services.*.source`` references declared ``service_sources`` names."""
    if not isinstance(services, dict):
        return
    available = set(service_sources or {})
    for service_name, spec in services.items():
        if not isinstance(spec, dict) or "source" not in spec:
            continue
        source_name = str(spec.get("source", "")).strip()
        if not source_name:
            raise ConfigError(
                _("manifest services.{NAME}.source must be a non-empty name.").format(
                    NAME=service_name
                )
            )
        if source_name not in available:
            raise ConfigError(
                _(
                    "manifest services.{NAME}.source references unknown service_sources "
                    "entry {SOURCE!r}"
                ).format(NAME=service_name, SOURCE=source_name)
            )


def merge_service_sources(
    base: dict[str, str] | None,
    overlay: dict[str, str] | None,
) -> dict[str, str] | None:
    """Merge service source maps; overlay replaces entries with the same name."""
    merged = dict(base or {})
    if overlay:
        merged.update(overlay)
    return merged or None


def source_env_key(source_name: str) -> str:
    """Map ``service_sources`` name to ``ODPM_SOURCE_*`` env key."""
    return "ODPM_SOURCE_" + source_name.upper()
