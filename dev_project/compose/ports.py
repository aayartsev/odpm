"""Host published-port offset for compose documents (``ODPM_PORT_OFFSET``)."""

from __future__ import annotations

from typing import Any

from .. import constants
from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _

_logger = get_module_logger(__name__)

_MIN_HOST_PORT = 1
_MAX_HOST_PORT = 65535


def assert_host_port_in_range(port: int, *, context: str) -> int:
    """Return *port* or raise ``ConfigError`` when outside ``1..65535``."""
    if not isinstance(port, int) or isinstance(port, bool):
        raise ConfigError(
            _("Invalid host port {PORT!r} ({CONTEXT})").format(
                PORT=port, CONTEXT=context
            )
        )
    if port < _MIN_HOST_PORT or port > _MAX_HOST_PORT:
        raise ConfigError(
            _(
                "Host port {PORT} out of range 1..65535 ({CONTEXT})"
            ).format(PORT=port, CONTEXT=context)
        )
    return port


def parse_port_offset(raw: str | None) -> int:
    """Parse ``ODPM_PORT_OFFSET``; missing/empty → ``0``; invalid → warning + ``0``."""
    if raw is None:
        return 0
    value = str(raw).strip()
    if not value:
        return 0
    try:
        return int(value, 10)
    except ValueError:
        _logger.warning(
            _(
                "Invalid {ENV}={VALUE!r}; using 0"
            ).format(ENV=constants.ODPM_PORT_OFFSET_ENV, VALUE=raw),
        )
        return 0


def _shift_host_port(host: int, offset: int, *, context: str) -> int:
    return assert_host_port_in_range(host + offset, context=context)


def _split_proto(spec: str) -> tuple[str, str]:
    if "/" in spec:
        body, proto = spec.rsplit("/", 1)
        return body, f"/{proto}"
    return spec, ""


def shift_published_port_spec(spec: Any, offset: int) -> Any:
    """Shift the host side of a Compose port publish by *offset*."""
    if offset == 0:
        return spec
    if isinstance(spec, dict):
        published = spec.get("published")
        if published is None:
            return spec
        try:
            host = int(published)
        except (TypeError, ValueError):
            _logger.warning(
                _("Leaving unparseable compose port dict unchanged: %r"), spec
            )
            return spec
        shifted = _shift_host_port(
            host, offset, context=f"published={published!r}"
        )
        updated = dict(spec)
        updated["published"] = shifted
        return updated
    if not isinstance(spec, str):
        return spec
    value = spec.strip()
    if not value:
        return value
    if value.startswith("["):
        _logger.warning(_("Leaving IPv6 compose port unchanged: %r"), value)
        return value
    body, proto_suffix = _split_proto(value)
    parts = body.split(":")
    if len(parts) == 1:
        _logger.warning(
            _("Leaving bare container-only compose port unchanged: %r"), value
        )
        return value
    if len(parts) == 2:
        host_s, container = parts
        try:
            host = int(host_s)
        except ValueError:
            _logger.warning(_("Leaving unparseable compose port unchanged: %r"), value)
            return value
        shifted = _shift_host_port(host, offset, context=value)
        return f"{shifted}:{container}{proto_suffix}"
    if len(parts) >= 3:
        # IP:HOST:CONTAINER… (host IP may contain dots; take penultimate as host)
        host_s = parts[-2]
        container = parts[-1]
        ip_prefix = ":".join(parts[:-2])
        try:
            host = int(host_s)
        except ValueError:
            _logger.warning(_("Leaving unparseable compose port unchanged: %r"), value)
            return value
        shifted = _shift_host_port(host, offset, context=value)
        return f"{ip_prefix}:{shifted}:{container}{proto_suffix}"
    _logger.warning(_("Leaving unparseable compose port unchanged: %r"), value)
    return value


def apply_host_port_offset(services: dict[str, Any], offset: int) -> None:
    """Mutate *services* in place: shift host side of every ``ports`` entry."""
    if offset == 0:
        return
    for service in services.values():
        if not isinstance(service, dict):
            continue
        ports = service.get("ports")
        if not isinstance(ports, list):
            continue
        service["ports"] = [
            shift_published_port_spec(item, offset) for item in ports
        ]
