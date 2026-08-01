"""Gate and helpers for ${@secret:} refs against .odpm/secrets.json."""

from __future__ import annotations

from typing import Any

from ...errors import ConfigError
from ...project_env.secrets import read_secrets_source, secrets_source_path
from ...translations import _
from .env_substitution import collect_secret_refs_in_value


def load_secrets_map(project_dir: str) -> dict[str, str]:
    """Return secrets from ``.odpm/secrets.json``, or ``{}`` when the file is absent."""
    loaded = read_secrets_source(project_dir)
    return dict(loaded) if loaded is not None else {}


def ensure_secrets_available_for_refs(
    project_dir: str,
    *trees: Any,
) -> dict[str, str]:
    """Load secrets when ``${@secret:}`` refs are present; require source file.

    Returns the secrets map (empty when there are no refs). Raises
    :class:`ConfigError` when refs exist but ``.odpm/secrets.json`` is missing
    (caller must have already applied ``--secrets-file`` import if any).
    """
    refs: set[str] = set()
    for tree in trees:
        refs.update(collect_secret_refs_in_value(tree))
    if not refs:
        return load_secrets_map(project_dir)

    source_path = secrets_source_path(project_dir)
    loaded = read_secrets_source(project_dir)
    if loaded is None:
        raise ConfigError(
            _(
                "Manifest references secrets (@secret) but .odpm/secrets.json "
                "is missing; create it or pass --secrets-file "
                "(required keys: {KEYS})"
            ).format(KEYS=", ".join(sorted(refs)))
        )
    return dict(loaded)
