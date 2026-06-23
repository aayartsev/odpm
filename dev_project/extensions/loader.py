"""Extension plugin load-time API version checks (4.6+)."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from .api import EXTENSION_API_VERSION, assert_extension_api_compatible

_DEFAULT_PLUGIN_API_VERSION = "1.0"


def resolve_plugin_api_version(plugin: Any) -> str:
    """Return declared API version for a plugin object or module (default 1.0)."""
    if isinstance(plugin, ModuleType):
        return str(getattr(plugin, "EXTENSION_API_VERSION", _DEFAULT_PLUGIN_API_VERSION))
    direct = getattr(plugin, "EXTENSION_API_VERSION", None)
    if direct is not None:
        return str(direct)
    type_version = getattr(type(plugin), "EXTENSION_API_VERSION", None)
    if type_version is not None:
        return str(type_version)
    return _DEFAULT_PLUGIN_API_VERSION


def validate_plugin_api(plugin: Any, *, plugin_id: str = "") -> None:
    """Raise :class:`ConfigError` when a loaded plugin targets an unsupported API."""
    version = resolve_plugin_api_version(plugin).strip()
    assert_extension_api_compatible(version, plugin_id=plugin_id)


def validate_pluggy_manager_plugins(manager: Any) -> None:
    """Validate API versions for all plugins registered on a pluggy manager."""
    for name, plugin in manager.list_name_plugin():
        validate_plugin_api(plugin, plugin_id=str(name))
