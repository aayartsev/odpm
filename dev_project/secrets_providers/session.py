"""Per-process secrets fetch session (one Infisical snapshot per odpm run)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SecretsFetchSession:
    """Idempotency flag for ``ensure_secrets_source`` within one process."""

    fetched: bool = False
    provider_name: str = ""
    key_count: int = 0


def session_for_config(config: object) -> SecretsFetchSession:
    """Return the session attached to *config*, creating one if needed."""
    existing = getattr(config, "secrets_fetch_session", None)
    if isinstance(existing, SecretsFetchSession):
        return existing
    session = SecretsFetchSession()
    try:
        config.secrets_fetch_session = session  # type: ignore[attr-defined]
    except Exception:
        pass
    return session
