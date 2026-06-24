"""Manifest compose naming policy (stdlib-only; safe for container import paths)."""

from __future__ import annotations

from typing import Any

from ..errors import ConfigError
from ..translations import _

RESERVED_MANIFEST_SERVICE_NAMES = frozenset({"odoo", "db", "postgres"})


def validate_manifest_compose_services(services: dict[str, Any] | None) -> None:
    """Reject reserved built-in names in manifest ``services`` (ADR-009)."""
    if not isinstance(services, dict):
        return
    for name in services:
        if name in RESERVED_MANIFEST_SERVICE_NAMES:
            raise ConfigError(
                _(
                    "manifest services.{NAME} is reserved; use service_patches.{NAME} to patch built-in services"
                ).format(NAME=name)
            )


def reject_reserved_compose_service_name(name: str, *, source: str) -> None:
    if name in RESERVED_MANIFEST_SERVICE_NAMES:
        raise ConfigError(
            _(
                "{SOURCE} cannot declare reserved compose service {NAME}; use manifest service_patches instead"
            ).format(SOURCE=source, NAME=name)
        )
