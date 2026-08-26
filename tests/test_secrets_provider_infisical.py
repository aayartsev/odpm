"""Tests for InfisicalSecretsProvider with an injected transport."""

from __future__ import annotations

import unittest
import urllib.request

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.secrets_providers.infisical_provider import InfisicalSecretsProvider


class _FakeInfisicalTransport:
    def __init__(self, secrets: dict[str, str]) -> None:
        self.secrets = secrets
        self.login_calls = 0
        self.list_calls = 0
        self.urls: list[str] = []

    def __call__(self, request: urllib.request.Request, timeout: float):
        del timeout
        self.urls.append(request.full_url)
        if "universal-auth/login" in request.full_url:
            self.login_calls += 1
            return {"accessToken": "tok"}
        self.list_calls += 1
        return {
            "secrets": [
                {"secretKey": key, "secretValue": value}
                for key, value in self.secrets.items()
            ]
        }


class InfisicalSecretsProviderTests(unittest.TestCase):
    def _credentials(self) -> dict[str, str]:
        return {
            constants.INFISICAL_CLIENT_ID_ENV: "client",
            constants.INFISICAL_CLIENT_SECRET_ENV: "secret",
        }

    def _config(self, **overrides) -> dict:
        payload = {
            "type": "infisical",
            "project_id": "proj",
            "environment_slug": "dev",
            "secret_path": "/odoo",
        }
        payload.update(overrides)
        return payload

    def test_maps_and_filters_keys(self):
        transport = _FakeInfisicalTransport(
            {"PAYMENT_API_KEY": "sk_live", "OTHER": "x"}
        )
        provider = InfisicalSecretsProvider(transport=transport)
        secrets = provider.fetch(
            provider_config=self._config(
                key_map={"PAYMENT_API_KEY": "payment_provider.api_key"},
                keys=["payment_provider.api_key"],
            ),
            credentials=self._credentials(),
            project_dir="/tmp",
        )
        self.assertEqual(secrets, {"payment_provider.api_key": "sk_live"})
        self.assertEqual(transport.login_calls, 1)
        self.assertEqual(transport.list_calls, 1)
        self.assertNotIn("sk_live", "".join(transport.urls))

    def test_missing_mapped_keys_raise(self):
        provider = InfisicalSecretsProvider(
            transport=_FakeInfisicalTransport({"OTHER": "x"})
        )
        with self.assertRaises(ConfigError) as ctx:
            provider.fetch(
                provider_config=self._config(keys=["payment_provider.api_key"]),
                credentials=self._credentials(),
                project_dir="/tmp",
            )
        self.assertIn("payment_provider.api_key", str(ctx.exception))

    def test_missing_credentials_raise(self):
        provider = InfisicalSecretsProvider(
            transport=_FakeInfisicalTransport({})
        )
        with self.assertRaises(ConfigError) as ctx:
            provider.fetch(
                provider_config=self._config(),
                credentials={},
                project_dir="/tmp",
            )
        self.assertIn(constants.INFISICAL_CLIENT_ID_ENV, str(ctx.exception))
        self.assertIn(constants.INFISICAL_CLIENT_SECRET_ENV, str(ctx.exception))

    def test_one_to_one_without_key_map(self):
        provider = InfisicalSecretsProvider(
            transport=_FakeInfisicalTransport({"api.token": "t"})
        )
        secrets = provider.fetch(
            provider_config=self._config(),
            credentials=self._credentials(),
            project_dir="/tmp",
        )
        self.assertEqual(secrets, {"api.token": "t"})


if __name__ == "__main__":
    unittest.main()
