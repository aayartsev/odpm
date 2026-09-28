"""Tests for secrets provider type precedence."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.errors import ConfigError
from dev_project.secrets_providers.registry import (
    clear_secrets_providers_for_tests,
    get_secrets_provider,
)
from dev_project.secrets_providers.resolve import (
    effective_infisical_config,
    merge_environ_with_dotenv,
    resolve_secrets_provider_name,
)


class SecretsProviderResolveTests(unittest.TestCase):
    def test_default_is_file(self):
        self.assertEqual(
            resolve_secrets_provider_name(OdpmCliArgs(), {}, None),
            constants.SECRETS_PROVIDER_FILE,
        )

    def test_manifest_then_env_then_cli(self):
        self.assertEqual(
            resolve_secrets_provider_name(OdpmCliArgs(), {}, "infisical"),
            "infisical",
        )
        self.assertEqual(
            resolve_secrets_provider_name(
                OdpmCliArgs(),
                {constants.ODPM_SECRETS_PROVIDER_ENV: "plugin"},
                "infisical",
            ),
            "plugin",
        )
        self.assertEqual(
            resolve_secrets_provider_name(
                OdpmCliArgs(secrets_provider="cli"),
                {constants.ODPM_SECRETS_PROVIDER_ENV: "plugin"},
                "infisical",
            ),
            "cli",
        )

    def test_secrets_file_forces_file(self):
        self.assertEqual(
            resolve_secrets_provider_name(
                OdpmCliArgs(secrets_file="/tmp/x.json", secrets_provider="infisical"),
                {constants.ODPM_SECRETS_PROVIDER_ENV: "infisical"},
                "infisical",
            ),
            constants.SECRETS_PROVIDER_FILE,
        )

    def test_process_env_wins_over_dotenv(self):
        merged = merge_environ_with_dotenv(
            {constants.INFISICAL_HOST_ENV: "https://from-process"},
            {constants.INFISICAL_HOST_ENV: "https://from-dotenv"},
        )
        self.assertEqual(merged[constants.INFISICAL_HOST_ENV], "https://from-process")

    def test_effective_infisical_config_requires_one_project_selector(self):
        with self.assertRaises(ConfigError):
            effective_infisical_config(
                {"project_id": "id"},
                {},
            )
        with self.assertRaises(ConfigError):
            effective_infisical_config(
                {"environment_slug": "dev"},
                {},
            )
        with self.assertRaises(ConfigError):
            effective_infisical_config(
                {
                    "project_id": "id",
                    "project_slug": "slug",
                    "environment_slug": "dev",
                },
                {},
            )

    def test_effective_infisical_config_env_overrides(self):
        config = effective_infisical_config(
            {
                "host": "https://app.example/",
                "project_id": "proj",
                "environment_slug": "dev",
            },
            {
                constants.INFISICAL_HOST_ENV: "https://self-hosted.example/",
                constants.INFISICAL_ENVIRONMENT_SLUG_ENV: "staging",
            },
        )
        self.assertEqual(config["host"], "https://self-hosted.example")
        self.assertEqual(config["environment_slug"], "staging")
        self.assertEqual(config["project_id"], "proj")
        self.assertIsNone(config["project_slug"])


class SecretsProviderRegistryTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_secrets_providers_for_tests()

    def test_builtins_file_and_infisical(self):
        self.assertEqual(get_secrets_provider("file").name, "file")
        self.assertEqual(get_secrets_provider("infisical").name, "infisical")

    def test_unknown_provider_raises(self):
        with self.assertRaises(ConfigError) as ctx:
            get_secrets_provider("no-such-provider")
        self.assertIn("no-such-provider", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
