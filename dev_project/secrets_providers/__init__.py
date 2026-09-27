"""Secrets source providers (file, Infisical, third-party entry points).

``SecretsFetchSession`` is a leaf type in :mod:`.session`. Heavier fetch /
registry wiring loads lazily so ``config`` can import the session without a
cycle through this package ``__init__``.
"""

from __future__ import annotations

import importlib
from typing import Any

from .session import SecretsFetchSession

__all__ = (
    "SecretsFetchSession",
    "SecretsProvider",
    "ensure_secrets_source",
    "ensure_secrets_source_for_config",
    "get_secrets_provider",
    "register_secrets_provider",
    "session_for_config",
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "SecretsProvider": (".protocol", "SecretsProvider"),
    "ensure_secrets_source": (".fetch", "ensure_secrets_source"),
    "ensure_secrets_source_for_config": (".fetch", "ensure_secrets_source_for_config"),
    "get_secrets_provider": (".registry", "get_secrets_provider"),
    "register_secrets_provider": (".registry", "register_secrets_provider"),
    "session_for_config": (".session", "session_for_config"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is not None:
        module_name, attr_name = target
        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)
    try:
        return importlib.import_module(f".{name}", __name__)
    except ModuleNotFoundError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(_LAZY_EXPORTS))
