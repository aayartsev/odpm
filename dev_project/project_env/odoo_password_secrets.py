"""Bootstrap ensure of Odoo password keys in ``.odpm/secrets.json`` (hardened)."""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .. import constants
from ..config.transforms.env_substitution import collect_secret_refs_in_value
from ..logging import get_module_logger
from ..manifest.secrets_policy import is_secret_placeholder
from ..project_env.secrets import read_secrets_source, write_secrets_source
from ..secrets_providers.resolve import (
    dotenv_dict_from_user_env,
    merge_environ_with_dotenv,
    resolve_secrets_provider_name,
)
from ..security_profiles import ODOO_PASSWORD_SECRET_KEYS

if TYPE_CHECKING:
    from ..config.config import Config

_logger = get_module_logger(__name__)


def _raw_password_field(raw: dict[str, Any], *path: str) -> str | None:
    node: Any = raw
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    if node is None:
        return None
    return str(node)


def raw_settings_references_password_secrets(raw: dict[str, Any]) -> set[str]:
    """Return Odoo password secret keys referenced via ``${@secret:}`` in settings."""
    refs = collect_secret_refs_in_value(raw)
    return {key for key in ODOO_PASSWORD_SECRET_KEYS if key in refs}


def warn_hardened_plaintext_password_fields(config: Config, raw: dict[str, Any]) -> None:
    """WARNING when hardened settings store passwords without ``${@secret:}`` (raw)."""
    from ..translations import _

    policy = getattr(config, "policy", None)
    if policy is None or not policy.should_bootstrap_odoo_password_secrets():
        return

    fields: list[tuple[str, str | None]] = [
        ("db_manager_password", _raw_password_field(raw, "db_manager_password")),
        (
            "db_creation_data.db_default_admin_password",
            _raw_password_field(raw, "db_creation_data", "db_default_admin_password"),
        ),
    ]
    for field_name, value in fields:
        if value is None or not value.strip():
            _logger.warning(
                _(
                    "Security profile hardened: {FIELD} is missing or empty in "
                    "user_settings.json; prefer ${{@secret:...}} (file not modified)"
                ).format(FIELD=field_name)
            )
            continue
        if "${@secret:" not in value:
            _logger.warning(
                _(
                    "Security profile hardened: {FIELD} in user_settings.json is not a "
                    "${{@secret:...}} reference (file not modified)"
                ).format(FIELD=field_name)
            )


def maybe_ensure_odoo_password_keys(
    config: Config,
    *,
    raw_manifest: Mapping[str, Any] | None = None,
) -> bool:
    """Create/merge Odoo password secrets per security-profile ensure table.

    Returns True when the secrets source was written.
    """
    policy = getattr(config, "policy", None)
    if policy is None or not policy.should_bootstrap_odoo_password_secrets():
        return False

    arguments = getattr(config, "arguments", None)
    if arguments is not None and getattr(arguments, "secrets_file", None):
        return False

    user_env = getattr(config, "user_env", None)
    environ = merge_environ_with_dotenv(
        os.environ,
        dotenv_dict_from_user_env(user_env),
    )
    bootstrap = getattr(config, "bootstrap", None)
    if raw_manifest is None:
        view = getattr(bootstrap, "manifest_view", None) if bootstrap is not None else None
        raw_manifest = getattr(view, "source_raw", None) if view is not None else None
    manifest_type = None
    if isinstance(raw_manifest, dict):
        from ..manifest.scenario_overrides import resolve_effective_manifest_slice

        slice_ = resolve_effective_manifest_slice(
            dict(raw_manifest),
            str(getattr(user_env, "odpm_scenario", "") or constants.DEFAULT_ODPM_SCENARIO),
        )
        if slice_.secrets is not None and slice_.secrets.provider is not None:
            manifest_type = slice_.secrets.provider.type

    provider_name = resolve_secrets_provider_name(arguments, environ, manifest_type)
    if provider_name != constants.SECRETS_PROVIDER_FILE:
        return False

    wrote_defaults = bool(
        bootstrap is not None
        and getattr(bootstrap, "wrote_hardened_password_defaults", False)
    )
    disk_raw = (
        getattr(bootstrap, "raw_user_settings_disk", None) if bootstrap is not None else None
    )
    if not isinstance(disk_raw, dict):
        disk_raw = {}

    if wrote_defaults:
        keys_needed = set(ODOO_PASSWORD_SECRET_KEYS)
    else:
        keys_needed = raw_settings_references_password_secrets(disk_raw)
    if not keys_needed:
        return False

    project_dir = str(getattr(config, "project_dir", "") or "")
    existing = read_secrets_source(project_dir) or {}
    merged = dict(existing)
    changed = False
    for key in keys_needed:
        current = merged.get(key)
        if current is None or is_secret_placeholder(current):
            merged[key] = secrets.token_urlsafe(32)
            changed = True
    if not changed:
        return False
    write_secrets_source(project_dir, merged)
    _logger.info(
        "Ensured Odoo password secret keys in .odpm/secrets.json (%s)",
        ", ".join(sorted(keys_needed)),
    )
    return True
