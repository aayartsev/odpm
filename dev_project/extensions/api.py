"""Stable extension API version marker for third-party plugins (4.5+)."""

from __future__ import annotations

from ..errors import ConfigError
from ..translations import _

EXTENSION_API_VERSION = "1.0"

SUPPORTED_EXTENSION_API_VERSIONS = frozenset({EXTENSION_API_VERSION})


def assert_extension_api_compatible(
    requested_version: str,
    *,
    plugin_id: str = "",
) -> None:
    """Raise :class:`ConfigError` when a plugin targets an unsupported API version."""
    version = str(requested_version).strip()
    if version in SUPPORTED_EXTENSION_API_VERSIONS:
        return
    label = f" ({plugin_id})" if plugin_id else ""
    message = _(
        "Unsupported odpm extension API version {VERSION}{LABEL}; "
        "supported versions: {SUPPORTED}."
    ).format(
        VERSION=version,
        LABEL=label,
        SUPPORTED=", ".join(sorted(SUPPORTED_EXTENSION_API_VERSIONS)),
    )
    raise ConfigError(message)
