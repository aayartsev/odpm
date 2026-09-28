"""Compose logical vs physical network naming (4.7 track D)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .. import constants
from ..logging import get_module_logger
from ..translations import _
from .service_names import ComposeNamingContext

_logger = get_module_logger(__name__)

LOGICAL_STACK_NETWORK = "stack"

_VALID_COMPOSE_NETWORK = re.compile(r"^[a-z][a-z0-9-]*$")


@dataclass(frozen=True)
class ComposeNetworkContext:
    """Resolved compose network from ``.env`` (inactive when ``logical_name`` is None)."""

    logical_name: str | None
    physical_name: str | None
    external: bool

    @property
    def is_active(self) -> bool:
        return self.logical_name is not None


def parse_compose_network_name(raw: str | None) -> str | None:
    """Return canonical logical network name, or ``None`` when unset/invalid."""
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if not _VALID_COMPOSE_NETWORK.fullmatch(value):
        _logger.warning(
            _(
                "Invalid {ENV}={VALUE!r} (use lowercase letters, digits, '-'; "
                "must start with a letter); compose network disabled"
            ).format(ENV=constants.ODPM_COMPOSE_NETWORK_ENV, VALUE=raw),
        )
        return None
    return value


def parse_compose_network_external(raw: str | None) -> bool:
    """Return whether the compose network is external (pre-existing on the host)."""
    value = (raw or "").strip().lower()
    if not value or value in {"0", "false", "no", "off", "n"}:
        return False
    if value in {"1", "true", "yes", "on", "y"}:
        return True
    _logger.warning(
        _(
            "Unknown {ENV}={VALUE!r}, using managed network"
        ).format(
            ENV=constants.ODPM_COMPOSE_NETWORK_EXTERNAL_ENV,
            VALUE=raw,
        ),
    )
    return False


def resolve_compose_network(
    *,
    network_raw: str | None,
    external_raw: str | None,
    naming: ComposeNamingContext,
) -> ComposeNetworkContext:
    """Build logical/physical network names from ``.env`` and compose prefix context."""
    logical = parse_compose_network_name(network_raw)
    if logical is None:
        return ComposeNetworkContext(
            logical_name=None,
            physical_name=None,
            external=False,
        )

    external = parse_compose_network_external(external_raw)
    if external:
        return ComposeNetworkContext(
            logical_name=logical,
            physical_name=logical,
            external=True,
        )

    prefix = naming.compose_prefix
    physical = f"{prefix}{logical}" if prefix else logical
    return ComposeNetworkContext(
        logical_name=logical,
        physical_name=physical,
        external=False,
    )


def attach_logical_compose_network(
    document: dict[str, Any], net_ctx: ComposeNetworkContext
) -> dict[str, Any]:
    """Declare logical ``networks:`` and attach services that omit ``networks``."""
    if not net_ctx.is_active or not net_ctx.logical_name:
        return document

    logical = net_ctx.logical_name
    if net_ctx.external:
        document["networks"] = {logical: {"external": True}}
    else:
        document["networks"] = {logical: {"driver": "bridge"}}

    services = document.get("services")
    if not isinstance(services, dict):
        return document
    for spec in services.values():
        if isinstance(spec, dict) and "networks" not in spec:
            spec["networks"] = [logical]
    return document


def _rewrite_network_name_list(
    items: list[Any], net_ctx: ComposeNetworkContext
) -> list[Any]:
    logical = net_ctx.logical_name
    physical = net_ctx.physical_name
    if not logical or not physical or logical == physical:
        return items
    rewritten: list[Any] = []
    for item in items:
        if isinstance(item, str) and item == logical:
            rewritten.append(physical)
        else:
            rewritten.append(item)
    return rewritten


def apply_compose_network(
    document: dict[str, Any],
    net_ctx: ComposeNetworkContext,
    _naming_ctx: ComposeNamingContext,
) -> dict[str, Any]:
    """Rewrite logical network keys and ``service.networks`` to physical names."""
    if not net_ctx.is_active or not net_ctx.logical_name or not net_ctx.physical_name:
        return document

    logical = net_ctx.logical_name
    physical = net_ctx.physical_name
    networks = document.get("networks")
    if isinstance(networks, dict) and logical in networks and logical != physical:
        networks[physical] = networks.pop(logical)

    services = document.get("services")
    if not isinstance(services, dict):
        return document
    for spec in services.values():
        if not isinstance(spec, dict):
            continue
        value = spec.get("networks")
        if isinstance(value, list):
            spec["networks"] = _rewrite_network_name_list(value, net_ctx)
    return document


def compose_network_from_user_env(user_env) -> ComposeNetworkContext:
    """Build network context from ``CreateUserEnvironment`` / ``ParsedUserEnv`` fields."""
    logical = getattr(user_env, "compose_network_logical", None)
    if not isinstance(logical, str) or not logical:
        logical = None
    physical = getattr(user_env, "compose_network_physical", None)
    if not isinstance(physical, str) or not physical:
        physical = None
    external = bool(getattr(user_env, "compose_network_external", False))
    return ComposeNetworkContext(
        logical_name=logical,
        physical_name=physical,
        external=external,
    )
