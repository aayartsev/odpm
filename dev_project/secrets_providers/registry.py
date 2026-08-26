"""Built-in and entry-point secrets providers."""

from __future__ import annotations

from .. import constants
from ..errors import ConfigError
from ..translations import _
from .file_provider import FileSecretsProvider
from .protocol import SecretsProvider

_PROVIDERS: dict[str, SecretsProvider] = {}
_ENTRY_POINTS_LOADED = False


def register_secrets_provider(provider: SecretsProvider) -> None:
    name = str(getattr(provider, "name", "") or "").strip()
    if not name:
        raise ValueError("secrets provider must have a non-empty name")
    _PROVIDERS[name] = provider


def clear_secrets_providers_for_tests() -> None:
    """Reset registry to built-ins (tests only)."""
    global _ENTRY_POINTS_LOADED
    _PROVIDERS.clear()
    _ENTRY_POINTS_LOADED = False
    _register_builtins()


def _register_builtins() -> None:
    if constants.SECRETS_PROVIDER_FILE not in _PROVIDERS:
        register_secrets_provider(FileSecretsProvider())
    if constants.SECRETS_PROVIDER_INFISICAL not in _PROVIDERS:
        from .infisical_provider import InfisicalSecretsProvider

        register_secrets_provider(InfisicalSecretsProvider())


def _load_entry_points() -> None:
    global _ENTRY_POINTS_LOADED
    if _ENTRY_POINTS_LOADED:
        return
    _ENTRY_POINTS_LOADED = True
    try:
        from importlib.metadata import entry_points
    except ImportError:
        return
    try:
        selected = entry_points(group="odpm.secrets_providers")
    except TypeError:
        selected = entry_points().get("odpm.secrets_providers", ())
    for entry in selected:
        loaded = entry.load()
        provider = loaded() if callable(loaded) and not hasattr(loaded, "fetch") else loaded
        if hasattr(provider, "name") and hasattr(provider, "fetch"):
            register_secrets_provider(provider)


def get_secrets_provider(name: str) -> SecretsProvider:
    _register_builtins()
    _load_entry_points()
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise ConfigError(
            _("Unknown secrets provider: {NAME}").format(NAME=name)
        )
    return provider
