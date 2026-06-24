"""Tests for manifest ${VAR} / ${VAR:-default} substitution."""

from __future__ import annotations

import unittest
from unittest import mock

from dev_project.config.transforms.env_substitution import (
    ODPM_JSON_ENV_EXPAND_FIELDS,
    EnvResolver,
    expand_env_in_compose_service_map,
    expand_env_in_json,
    expand_env_string,
    merged_subprocess_environ,
)
from dev_project.errors import ConfigError


class EnvResolverTests(unittest.TestCase):
    def test_resolve_prefers_process_environ_over_project_dotenv(self):
        resolver = EnvResolver.from_sources(
            process_environ={"GIT_HOST": "from-process"},
            project_dotenv={"GIT_HOST": "from-dotenv"},
        )
        self.assertEqual(resolver.resolve("GIT_HOST"), "from-process")

    def test_resolve_falls_back_to_project_dotenv(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={"PLATFORM_DIR": "/tmp/platform"},
        )
        self.assertEqual(resolver.resolve("PLATFORM_DIR"), "/tmp/platform")

    def test_resolve_returns_none_when_unset(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        self.assertIsNone(resolver.resolve("MISSING"))

    def test_from_user_env_uses_project_dotenv_dict(self):
        user_env = mock.MagicMock()
        user_env.project_dotenv_dict.return_value = {"PLATFORM_DIR": "/tmp/platform"}
        resolver = EnvResolver.from_user_env(
            user_env,
            process_environ={"GIT_HOST": "from-process"},
        )
        self.assertEqual(resolver.resolve("GIT_HOST"), "from-process")
        self.assertEqual(resolver.resolve("PLATFORM_DIR"), "/tmp/platform")
        user_env.project_dotenv_dict.assert_called_once_with()


class ExpandEnvStringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = EnvResolver.from_sources(
            process_environ={"GIT_HOST": "git.company.example"},
            project_dotenv={"ODOO_PLATFORM_DIR": "/home/dev/odoo/19.0"},
        )

    def test_expands_file_url_from_dotenv(self):
        result = expand_env_string(
            "file://${ODOO_PLATFORM_DIR}",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "file:///home/dev/odoo/19.0")

    def test_expands_git_url_from_process_environ(self):
        result = expand_env_string(
            "https://${GIT_HOST}/company/extra.git 17.0",
            self.resolver,
            field_path="dependencies[]",
        )
        self.assertEqual(
            result,
            "https://git.company.example/company/extra.git 17.0",
        )

    def test_expands_default_when_var_missing(self):
        result = expand_env_string(
            "file://${MISSING:-/default/path}",
            self.resolver,
            field_path="developing_project",
        )
        self.assertEqual(result, "file:///default/path")

    def test_missing_var_without_default_raises_config_error(self):
        with self.assertRaises(ConfigError) as ctx:
            expand_env_string(
                "file://${MISSING}",
                self.resolver,
                field_path="odoo_git_link",
            )
        self.assertIn("MISSING", str(ctx.exception))
        self.assertIn("odoo_git_link", str(ctx.exception))

    def test_dollar_dollar_escape(self):
        result = expand_env_string(
            "cost is $$100",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "cost is $100")

    def test_dollar_escape_before_expansion(self):
        result = expand_env_string(
            "file://$$${ODOO_PLATFORM_DIR}",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "file://$/home/dev/odoo/19.0")

    def test_string_without_dollar_unchanged(self):
        result = expand_env_string(
            "file:///fixed/path",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "file:///fixed/path")


class ExpandEnvInJsonTests(unittest.TestCase):
    def test_expands_whitelist_fields_only(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={
                "PLATFORM": "/tmp/odoo",
                "DEP": "/tmp/oca/web",
            },
        )
        raw = {
            "odoo_version": "17.${ODOO_VER}",
            "odoo_git_link": "file://${PLATFORM}",
            "dependencies": [
                "file://${DEP}",
                "https://github.com/OCA/sale.git 17.0",
            ],
            "requirements_txt": ["${PIP_EXTRA}"],
        }
        expanded = expand_env_in_json(
            raw,
            resolver=resolver,
            allowed_fields=ODPM_JSON_ENV_EXPAND_FIELDS,
        )
        self.assertEqual(expanded["odoo_version"], "17.${ODOO_VER}")
        self.assertEqual(expanded["odoo_git_link"], "file:///tmp/odoo")
        self.assertEqual(
            expanded["dependencies"],
            ["file:///tmp/oca/web", "https://github.com/OCA/sale.git 17.0"],
        )
        self.assertEqual(expanded["requirements_txt"], ["${PIP_EXTRA}"])

    def test_non_dict_input_returned_unchanged(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        self.assertIsNone(
            expand_env_in_json(None, resolver=resolver, allowed_fields=frozenset())
        )


class ExpandComposeServiceMapTests(unittest.TestCase):
    def test_expands_services_and_patches_string_fields(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={"DATA_DIR": "/opt/autoparts/data"},
        )
        services = {
            "armtek": {
                "image": "autoparts_env:emulator",
                "user": "root",
                "volumes": ["${DATA_DIR}:/data:Z"],
                "environment": {"HOST": "${DATA_DIR}"},
                "command": ["sh", "-c", "echo ${DATA_DIR}"],
            }
        }
        expanded = expand_env_in_compose_service_map(
            services,
            resolver=resolver,
            field_prefix="services",
        )
        self.assertEqual(
            expanded,
            {
                "armtek": {
                    "image": "autoparts_env:emulator",
                    "user": "root",
                    "volumes": ["/opt/autoparts/data:/data:Z"],
                    "environment": {"HOST": "/opt/autoparts/data"},
                    "command": ["sh", "-c", "echo /opt/autoparts/data"],
                }
            },
        )

    def test_merged_subprocess_environ_prefers_process_over_dotenv(self):
        resolver = EnvResolver.from_sources(
            process_environ={"BUILD_DIR": "/from-process"},
            project_dotenv={"BUILD_DIR": "/from-dotenv", "ONLY_DOTENV": "yes"},
        )
        merged = merged_subprocess_environ(resolver)
        self.assertEqual(merged["BUILD_DIR"], "/from-process")
        self.assertEqual(merged["ONLY_DOTENV"], "yes")


if __name__ == "__main__":
    unittest.main()
