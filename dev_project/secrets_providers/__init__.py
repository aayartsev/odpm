"""Secrets source providers (file, Infisical, third-party entry points)."""

from .fetch import ensure_secrets_source, ensure_secrets_source_for_config
from .protocol import SecretsProvider
from .registry import get_secrets_provider, register_secrets_provider
from .session import SecretsFetchSession

__all__ = (
    "SecretsFetchSession",
    "SecretsProvider",
    "ensure_secrets_source",
    "ensure_secrets_source_for_config",
    "get_secrets_provider",
    "register_secrets_provider",
)
