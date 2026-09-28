"""Manifest compose naming policy (stdlib-only; safe for container import paths)."""

from __future__ import annotations

from typing import Any

from .. import constants
from ..compose.network_names import LOGICAL_STACK_NETWORK
from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _

_logger = get_module_logger(__name__)

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


def warn_manifest_compose_stack_network(
    services: dict[str, Any] | None,
    *,
    compose_network_logical: str | None,
) -> None:
    """Warn when sidecars reference logical ``stack`` without matching ``.env`` (ADR-014)."""
    if not isinstance(services, dict):
        return
    if compose_network_logical == LOGICAL_STACK_NETWORK:
        return
    for service_name, spec in services.items():
        if not isinstance(spec, dict):
            continue
        networks = spec.get("networks")
        if not isinstance(networks, list):
            continue
        for entry in networks:
            if entry != LOGICAL_STACK_NETWORK:
                continue
            _logger.warning(
                _(
                    "manifest services.{SVC}.networks references logical network {NET!r}; "
                    "set {ENV}={NET} in .env or remove explicit networks"
                ).format(
                    SVC=service_name,
                    NET=LOGICAL_STACK_NETWORK,
                    ENV=constants.ODPM_COMPOSE_NETWORK_ENV,
                )
            )


def reject_reserved_compose_service_name(name: str, *, source: str) -> None:
    if name in RESERVED_MANIFEST_SERVICE_NAMES:
        raise ConfigError(
            _(
                "{SOURCE} cannot declare reserved compose service {NAME}; use manifest service_patches instead"
            ).format(SOURCE=source, NAME=name)
        )
