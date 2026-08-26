"""Resolve secrets provider type, credentials, and Infisical config."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .. import constants
from ..errors import ConfigError
from ..host.cli.args import OdpmCliArgs
from ..translations import _


def merge_environ_with_dotenv(
    process_environ: Mapping[str, str] | None,
    project_dotenv: Mapping[str, str] | None,
) -> dict[str, str]:
    """Dotenv first, process env wins (same as :class:`EnvResolver`)."""
    merged = {str(key): str(value) for key, value in (project_dotenv or {}).items()}
    for key, value in (process_environ or {}).items():
        merged[str(key)] = str(value)
    return merged


def resolve_secrets_provider_name(
    arguments: OdpmCliArgs | None,
    environ: Mapping[str, str],
    manifest_provider_type: str | None,
) -> str:
    """CLI ``--secrets-provider`` > env > manifest > ``file``.

    ``--secrets-file`` forces the ``file`` provider for this run.
    """
    if arguments is not None and arguments.secrets_file:
        return constants.SECRETS_PROVIDER_FILE
    if arguments is not None:
        cli_name = (arguments.secrets_provider or "").strip()
        if cli_name:
            return cli_name
    env_name = str(environ.get(constants.ODPM_SECRETS_PROVIDER_ENV) or "").strip()
    if env_name:
        return env_name
    manifest_name = (manifest_provider_type or "").strip()
    if manifest_name:
        return manifest_name
    return constants.SECRETS_PROVIDER_FILE


def load_provider_credentials(environ: Mapping[str, str]) -> dict[str, str]:
    """Copy known credential keys from the merged environ."""
    keys = (
        constants.INFISICAL_CLIENT_ID_ENV,
        constants.INFISICAL_CLIENT_SECRET_ENV,
        constants.INFISICAL_HOST_ENV,
        constants.INFISICAL_ENVIRONMENT_SLUG_ENV,
        constants.ODPM_SECRETS_PROVIDER_ENV,
    )
    credentials: dict[str, str] = {}
    for key in keys:
        value = str(environ.get(key) or "").strip()
        if value:
            credentials[key] = value
    return credentials


def dotenv_dict_from_user_env(user_env: object | None) -> dict[str, str]:
    if user_env is None:
        return {}
    getter = getattr(user_env, "project_dotenv_dict", None)
    if not callable(getter):
        return {}
    value = getter()
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def effective_infisical_config(
    provider_config: Mapping[str, Any],
    environ: Mapping[str, str],
) -> dict[str, Any]:
    """Apply ``INFISICAL_HOST`` / ``INFISICAL_ENVIRONMENT_SLUG`` env overrides."""
    host = str(
        environ.get(constants.INFISICAL_HOST_ENV)
        or provider_config.get("host")
        or constants.DEFAULT_INFISICAL_HOST
    ).strip()
    host = host.rstrip("/") or constants.DEFAULT_INFISICAL_HOST

    project_id = str(provider_config.get("project_id") or "").strip() or None
    project_slug = str(provider_config.get("project_slug") or "").strip() or None
    if (project_id is None) == (project_slug is None):
        raise ConfigError(
            _("Infisical requires exactly one of project_id or project_slug")
        )

    environment_slug = str(
        environ.get(constants.INFISICAL_ENVIRONMENT_SLUG_ENV)
        or provider_config.get("environment_slug")
        or ""
    ).strip()
    if not environment_slug:
        raise ConfigError(_("Infisical environment_slug is required"))

    secret_path = str(provider_config.get("secret_path") or "/").strip() or "/"
    recursive = bool(provider_config.get("recursive", False))
    key_map_raw = provider_config.get("key_map") or {}
    key_map: dict[str, str] = {}
    if isinstance(key_map_raw, Mapping):
        for source_key, dest_key in key_map_raw.items():
            src = str(source_key).strip()
            dest = str(dest_key).strip()
            if src and dest:
                key_map[src] = dest

    keys_raw = provider_config.get("keys") or ()
    keys = tuple(str(item).strip() for item in keys_raw if str(item).strip())

    return {
        "host": host,
        "project_id": project_id,
        "project_slug": project_slug,
        "environment_slug": environment_slug,
        "secret_path": secret_path,
        "recursive": recursive,
        "key_map": key_map,
        "keys": keys,
    }
