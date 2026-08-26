"""Unit tests for the stdlib Infisical REST client."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import patch

from dev_project.errors import ConfigError
from dev_project.secrets_providers import infisical_client


class InfisicalClientUnitTests(unittest.TestCase):
    def test_normalize_host_strips_slash_and_defaults(self):
        self.assertEqual(
            infisical_client.normalize_infisical_host(
                "https://app.infisical.com/",
                default="https://app.infisical.com",
            ),
            "https://app.infisical.com",
        )
        self.assertEqual(
            infisical_client.normalize_infisical_host(
                "  ",
                default="https://app.infisical.com",
            ),
            "https://app.infisical.com",
        )

    def test_build_list_secrets_query_project_id(self):
        query = infisical_client.build_list_secrets_query(
            project_id="proj",
            project_slug=None,
            environment="dev",
            secret_path="/odoo",
            recursive=True,
        )
        self.assertIn("projectId=proj", query)
        self.assertNotIn("projectSlug", query)
        self.assertIn("environment=dev", query)
        self.assertIn("secretPath=%2Fodoo", query)
        self.assertIn("recursive=true", query)
        self.assertIn("viewSecretValue=true", query)

    def test_build_list_secrets_query_project_slug(self):
        query = infisical_client.build_list_secrets_query(
            project_id=None,
            project_slug="acme",
            environment="staging",
            secret_path="/",
            recursive=False,
        )
        self.assertIn("projectSlug=acme", query)
        self.assertNotIn("projectId", query)
        self.assertIn("recursive=false", query)

    def test_list_secrets_parses_camel_and_snake_case(self):
        payloads = [
            {
                "secrets": [
                    {"secretKey": "A", "secretValue": "1"},
                    {"secret_key": "B", "secret_value": "2"},
                    {"key": "C", "value": "3"},
                ]
            },
            {
                "secrets": {
                    "secrets": [
                        {"secretKey": "A", "secretValue": "1"},
                    ]
                }
            },
        ]
        first = infisical_client._extract_secret_pairs(payloads[0])
        self.assertEqual(first, {"A": "1", "B": "2", "C": "3"})
        nested = infisical_client._extract_secret_pairs(payloads[1])
        self.assertEqual(nested, {"A": "1"})

    def test_login_and_list_via_transport(self):
        calls: list[str] = []

        def transport(request: urllib.request.Request, timeout: float):
            del timeout
            calls.append(request.get_method() + " " + request.full_url)
            if "universal-auth/login" in request.full_url:
                return {"accessToken": "tok-1"}
            return {
                "secrets": [{"secretKey": "K", "secretValue": "secret-value"}]
            }

        token = infisical_client.login(
            "https://app.infisical.com",
            client_id="id",
            client_secret="secret",
            transport=transport,
        )
        self.assertEqual(token, "tok-1")
        secrets = infisical_client.list_secrets(
            "https://app.infisical.com",
            token,
            project_id="p",
            project_slug=None,
            environment="dev",
            secret_path="/",
            recursive=False,
            transport=transport,
        )
        self.assertEqual(secrets, {"K": "secret-value"})
        self.assertTrue(any("login" in item for item in calls))
        self.assertTrue(any("/api/v4/secrets" in item for item in calls))

    def test_http_error_omits_response_body(self):
        def fake_urlopen(request, timeout=None):
            del timeout
            body = io.BytesIO(
                json.dumps({"message": "leaked-token-value"}).encode("utf-8")
            )
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                Message(),
                body,
            )

        with patch(
            "dev_project.secrets_providers.infisical_client.urllib.request.urlopen",
            fake_urlopen,
        ):
            with self.assertRaises(ConfigError) as ctx:
                infisical_client.login(
                    "https://app.infisical.com",
                    client_id="id",
                    client_secret="secret",
                )
        message = str(ctx.exception)
        self.assertIn("401", message)
        self.assertIn("/api/v1/auth/universal-auth/login", message)
        self.assertNotIn("leaked-token-value", message)


if __name__ == "__main__":
    unittest.main()
