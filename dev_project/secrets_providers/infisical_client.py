"""Minimal Infisical REST client (stdlib urllib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any, Callable

from ..errors import ConfigError
from ..translations import _

DEFAULT_TIMEOUT_SECONDS = 30.0

JsonObject = dict[str, Any]
Transport = Callable[[urllib.request.Request, float], JsonObject]


def normalize_infisical_host(host: str, *, default: str) -> str:
    cleaned = (host or "").strip().rstrip("/")
    return cleaned or default


def _request_json(
    request: urllib.request.Request,
    timeout: float,
) -> JsonObject:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        path = urllib.parse.urlparse(request.full_url).path
        raise ConfigError(
            _("Infisical HTTP {STATUS} for {PATH}").format(
                STATUS=exc.code,
                PATH=path,
            )
        ) from exc
    except urllib.error.URLError as exc:
        raise ConfigError(
            _("Infisical request failed: {DETAIL}").format(DETAIL=exc.reason)
        ) from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(
            _("Infisical request failed: {DETAIL}").format(DETAIL="invalid JSON")
        ) from exc
    if not isinstance(payload, dict):
        raise ConfigError(
            _("Infisical request failed: {DETAIL}").format(DETAIL="invalid JSON object")
        )
    return payload


def login(
    host: str,
    *,
    client_id: str,
    client_secret: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transport: Transport | None = None,
) -> str:
    url = f"{host}/api/v1/auth/universal-auth/login"
    body = json.dumps(
        {"clientId": client_id, "clientSecret": client_secret}
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    sender = transport or _request_json
    payload = sender(request, timeout)
    token = payload.get("accessToken") or payload.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise ConfigError(
            _("Infisical request failed: {DETAIL}").format(DETAIL="missing accessToken")
        )
    return token.strip()


def build_list_secrets_query(
    *,
    project_id: str | None,
    project_slug: str | None,
    environment: str,
    secret_path: str,
    recursive: bool,
) -> str:
    params: list[tuple[str, str]] = [
        ("environment", environment),
        ("secretPath", secret_path),
        ("recursive", "true" if recursive else "false"),
        ("viewSecretValue", "true"),
    ]
    if project_id:
        params.append(("projectId", project_id))
    if project_slug:
        params.append(("projectSlug", project_slug))
    return urllib.parse.urlencode(params)


def _extract_secret_pairs(payload: Mapping[str, Any]) -> dict[str, str]:
    raw_secrets = payload.get("secrets")
    if isinstance(raw_secrets, dict):
        raw_secrets = raw_secrets.get("secrets", raw_secrets)
    if not isinstance(raw_secrets, list):
        return {}
    result: dict[str, str] = {}
    for item in raw_secrets:
        if not isinstance(item, dict):
            continue
        key = item.get("secretKey") or item.get("secret_key") or item.get("key")
        value = item.get("secretValue") or item.get("secret_value") or item.get("value")
        if isinstance(key, str) and key.strip() and isinstance(value, str):
            result[key.strip()] = value
    return result


def list_secrets(
    host: str,
    token: str,
    *,
    project_id: str | None,
    project_slug: str | None,
    environment: str,
    secret_path: str,
    recursive: bool,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transport: Transport | None = None,
) -> dict[str, str]:
    query = build_list_secrets_query(
        project_id=project_id,
        project_slug=project_slug,
        environment=environment,
        secret_path=secret_path,
        recursive=recursive,
    )
    url = f"{host}/api/v4/secrets?{query}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    sender = transport or _request_json
    payload = sender(request, timeout)
    return _extract_secret_pairs(payload)
