"""Infisical SecretsProvider adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .. import constants
from ..errors import ConfigError
from ..host.cli.args import OdpmCliArgs
from ..logging import get_module_logger
from ..translations import _
from . import infisical_client
from .infisical_client import Transport
from .resolve import effective_infisical_config

_logger = get_module_logger(__name__)


class InfisicalSecretsProvider:
    name = constants.SECRETS_PROVIDER_INFISICAL

    def __init__(self, transport: Transport | None = None) -> None:
        self._transport = transport

    def fetch(
        self,
        *,
        provider_config: Mapping[str, Any],
        credentials: Mapping[str, str],
        project_dir: str,
        arguments: OdpmCliArgs | None = None,
    ) -> dict[str, str]:
        del project_dir, arguments
        client_id = str(credentials.get(constants.INFISICAL_CLIENT_ID_ENV) or "").strip()
        client_secret = str(
            credentials.get(constants.INFISICAL_CLIENT_SECRET_ENV) or ""
        ).strip()
        if not client_id or not client_secret:
            needed = [
                constants.INFISICAL_CLIENT_ID_ENV,
                constants.INFISICAL_CLIENT_SECRET_ENV,
            ]
            raise ConfigError(
                _("Missing Infisical credentials: {KEYS}").format(
                    KEYS=", ".join(needed)
                )
            )

        config = effective_infisical_config(provider_config, credentials)
        host = infisical_client.normalize_infisical_host(
            str(config["host"]),
            default=constants.DEFAULT_INFISICAL_HOST,
        )
        token = infisical_client.login(
            host,
            client_id=client_id,
            client_secret=client_secret,
            transport=self._transport,
        )
        raw = infisical_client.list_secrets(
            host,
            token,
            project_id=config["project_id"],
            project_slug=config["project_slug"],
            environment=str(config["environment_slug"]),
            secret_path=str(config["secret_path"]),
            recursive=bool(config["recursive"]),
            transport=self._transport,
        )
        mapped = _apply_key_map(raw, config.get("key_map") or {})
        required_keys = tuple(config.get("keys") or ())
        if required_keys:
            missing = [key for key in required_keys if key not in mapped]
            if missing:
                raise ConfigError(
                    _("Infisical secrets missing after fetch: {KEYS}").format(
                        KEYS=", ".join(missing)
                    )
                )
            mapped = {key: mapped[key] for key in required_keys}
        _logger.debug(
            "Infisical list path=%s keys=%s",
            config["secret_path"],
            len(mapped),
        )
        return mapped


def _apply_key_map(
    secrets: Mapping[str, str],
    key_map: Mapping[str, str],
) -> dict[str, str]:
    if not key_map:
        return dict(secrets)
    result: dict[str, str] = {}
    for source_key, value in secrets.items():
        dest = key_map.get(source_key, source_key)
        result[dest] = value
    return result
