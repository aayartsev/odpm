"""Local sidecar enable/disable gates from ``user_settings.json``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _
from .service_names import LOGICAL_DB, LOGICAL_ODOO

if TYPE_CHECKING:
    from ..extensions.context import ExtensionHostContext

_logger = get_module_logger(__name__)

_RESERVED_COMPOSE_SERVICES = frozenset({LOGICAL_DB, LOGICAL_ODOO})


def parse_sidecar_gates(raw: Any) -> dict[str, bool]:
    """Parse ``user_settings.sidecars``; ``None`` / absent-shaped → empty map."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(
            _("user_settings.json sidecars must be an object of service name to boolean")
        )
    result: dict[str, bool] = {}
    for key, value in raw.items():
        name = str(key)
        if name in _RESERVED_COMPOSE_SERVICES:
            raise ConfigError(
                _(
                    "user_settings.json sidecars cannot include built-in service {NAME}"
                ).format(NAME=name)
            )
        if not isinstance(value, bool):
            raise ConfigError(
                _(
                    "user_settings.json sidecars.{NAME} must be a boolean (true or false)"
                ).format(NAME=name)
            )
        result[name] = value
    return result


def apply_sidecar_gates(
    services: dict[str, Any],
    gates: dict[str, bool],
) -> tuple[dict[str, Any], set[str]]:
    """Drop services with ``gates[name] is False``; warn on unknown gate keys.

    Returns ``(kept_services, dropped_names)``. Missing gate key keeps the service.
    """
    if not gates:
        return dict(services), set()
    known = set(services)
    for name in gates:
        if name not in known:
            _logger.warning(
                _(
                    "user_settings.json sidecars refers to unknown compose service {NAME}"
                ).format(NAME=name)
            )
    dropped: set[str] = set()
    kept: dict[str, Any] = {}
    for name, spec in services.items():
        if gates.get(name) is False:
            dropped.add(name)
            continue
        kept[name] = spec
    return kept, dropped


def scrub_service_deps(services: dict[str, Any], dropped: set[str]) -> None:
    """Remove dropped logical names from list-form ``depends_on`` / ``links``."""
    if not dropped:
        return
    for spec in services.values():
        if not isinstance(spec, dict):
            continue
        for field in ("depends_on", "links"):
            value = spec.get(field)
            if isinstance(value, list):
                spec[field] = [item for item in value if item not in dropped]


def collect_effective_compose_services(
    ext: ExtensionHostContext,
    gates: dict[str, bool],
) -> dict[str, Any]:
    """Manifest/plugin sidecars after local gates (plan / fragment materialize)."""
    from .fragments import collect_compose_services

    services = collect_compose_services(ext)
    kept, _dropped = apply_sidecar_gates(services, gates)
    return kept


def sidecar_gates_from_user_settings(user_settings: Any) -> dict[str, bool]:
    """Read gates from a settings slice; non-dict → empty."""
    raw = getattr(user_settings, "sidecars", None)
    if isinstance(raw, dict):
        return dict(raw)
    return {}
