"""Tests for security profiles (passwords + port binds)."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.config.transforms.env_substitution import (
    EnvResolver,
    expand_env_deep,
    with_secrets,
)
from dev_project.project_env.odoo_password_secrets import maybe_ensure_odoo_password_keys
from dev_project.project_env.secrets import read_secrets_source, write_secrets_source
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.security_profiles import (
    HARDENED_DB_DEFAULT_ADMIN_PASSWORD_REF,
    HARDENED_DB_MANAGER_PASSWORD_REF,
    ODPM_SECRET_KEY_DB_DEFAULT_ADMIN_PASSWORD,
    ODPM_SECRET_KEY_DB_MANAGER_PASSWORD,
    parse_security_profile,
    resolve_security_profile,
)


def _user_env(scenario: str = constants.SERVER_SCENARIO) -> MagicMock:
    env = MagicMock()
    env.odpm_scenario = scenario
    env._project_dotenv = {}
    return env


class SecurityProfileAxisTests(unittest.TestCase):
    def test_scenario_defaults(self):
        self.assertEqual(
            resolve_security_profile(constants.DEVELOPER_SCENARIO), "convenience"
        )
        self.assertEqual(
            resolve_security_profile(constants.SERVER_SCENARIO), "hardened"
        )
        self.assertEqual(resolve_security_profile(constants.CI_SCENARIO), "convenience")

    def test_parse_invalid(self):
        self.assertIsNone(parse_security_profile("nope"))
        self.assertEqual(parse_security_profile("HARDENED"), "hardened")

    def test_developer_hardened_binds_localhost(self):
        policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO, security_profile="hardened"
        )
        self.assertTrue(policy.bind_postgres_localhost)
        self.assertTrue(policy.bind_published_ports_localhost)
        self.assertTrue(policy.should_bootstrap_odoo_password_secrets())

    def test_server_convenience_opens_ports(self):
        policy = ScenarioPolicy.from_scenario(
            constants.SERVER_SCENARIO, security_profile="convenience"
        )
        self.assertFalse(policy.bind_postgres_localhost)
        self.assertFalse(policy.bind_published_ports_localhost)
        self.assertFalse(policy.should_bootstrap_odoo_password_secrets())

    def test_ci_ignores_hardened_port_override(self):
        policy = ScenarioPolicy.from_scenario(
            constants.CI_SCENARIO, security_profile="hardened"
        )
        self.assertTrue(policy.bind_postgres_localhost)
        self.assertFalse(policy.bind_published_ports_localhost)
        self.assertFalse(policy.should_bootstrap_odoo_password_secrets())


class OdooPasswordEnsureTests(unittest.TestCase):
    def test_ensure_on_wrote_hardened_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.project_dir = tmp
            config.policy = ScenarioPolicy.from_scenario(
                constants.SERVER_SCENARIO, security_profile="hardened"
            )
            config.arguments = MagicMock(secrets_file=None, secrets_provider=None)
            config.user_env = _user_env()
            config.bootstrap = MagicMock()
            config.bootstrap.wrote_hardened_password_defaults = True
            config.bootstrap.raw_user_settings_disk = {
                "db_manager_password": HARDENED_DB_MANAGER_PASSWORD_REF,
            }
            self.assertTrue(maybe_ensure_odoo_password_keys(config, raw_manifest={}))
            secrets = read_secrets_source(tmp)
            assert secrets is not None
            self.assertIn(ODPM_SECRET_KEY_DB_MANAGER_PASSWORD, secrets)
            self.assertIn(ODPM_SECRET_KEY_DB_DEFAULT_ADMIN_PASSWORD, secrets)

    def test_no_ensure_on_plaintext_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.project_dir = tmp
            config.policy = ScenarioPolicy.from_scenario(
                constants.SERVER_SCENARIO, security_profile="hardened"
            )
            config.arguments = MagicMock(secrets_file=None, secrets_provider=None)
            config.user_env = _user_env()
            config.bootstrap = MagicMock()
            config.bootstrap.wrote_hardened_password_defaults = False
            config.bootstrap.raw_user_settings_disk = {
                "db_manager_password": "1",
                "db_creation_data": {"db_default_admin_password": "admin"},
            }
            self.assertFalse(maybe_ensure_odoo_password_keys(config, raw_manifest={}))
            self.assertIsNone(read_secrets_source(tmp))

    def test_merge_ensure_when_refs_and_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_secrets_source(tmp, {"other.key": "x"})
            config = MagicMock()
            config.project_dir = tmp
            config.policy = ScenarioPolicy.from_scenario(
                constants.SERVER_SCENARIO, security_profile="hardened"
            )
            config.arguments = MagicMock(secrets_file=None, secrets_provider=None)
            config.user_env = _user_env()
            config.bootstrap = MagicMock()
            config.bootstrap.wrote_hardened_password_defaults = False
            config.bootstrap.raw_user_settings_disk = {
                "db_manager_password": HARDENED_DB_MANAGER_PASSWORD_REF,
            }
            self.assertTrue(maybe_ensure_odoo_password_keys(config, raw_manifest={}))
            secrets = read_secrets_source(tmp)
            assert secrets is not None
            self.assertEqual(secrets["other.key"], "x")
            self.assertIn(ODPM_SECRET_KEY_DB_MANAGER_PASSWORD, secrets)
            self.assertNotIn(ODPM_SECRET_KEY_DB_DEFAULT_ADMIN_PASSWORD, secrets)

    def test_secrets_file_skips_ensure(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.project_dir = tmp
            config.policy = ScenarioPolicy.from_scenario(
                constants.SERVER_SCENARIO, security_profile="hardened"
            )
            config.arguments = MagicMock(
                secrets_file="/tmp/x.json", secrets_provider=None
            )
            config.user_env = _user_env()
            config.bootstrap = MagicMock()
            config.bootstrap.wrote_hardened_password_defaults = True
            config.bootstrap.raw_user_settings_disk = {}
            self.assertFalse(maybe_ensure_odoo_password_keys(config, raw_manifest={}))


class ExpandEnvDeepTests(unittest.TestCase):
    def test_nested_secret_expand(self):
        resolver = with_secrets(
            EnvResolver(
                project_dotenv={},
                process_environ={**os.environ, "HOME": "/tmp/home"},
            ),
            {
                ODPM_SECRET_KEY_DB_MANAGER_PASSWORD: "secret-value",
                ODPM_SECRET_KEY_DB_DEFAULT_ADMIN_PASSWORD: "admin-secret",
            },
        )
        raw = {
            "db_manager_password": HARDENED_DB_MANAGER_PASSWORD_REF,
            "db_creation_data": {
                "db_default_admin_password": HARDENED_DB_DEFAULT_ADMIN_PASSWORD_REF,
            },
            "sql_queries": ["SELECT '${HOME}'"],
        }
        out = expand_env_deep(raw, resolver=resolver)
        self.assertEqual(out["db_manager_password"], "secret-value")
        self.assertEqual(
            out["db_creation_data"]["db_default_admin_password"], "admin-secret"
        )
        self.assertEqual(out["sql_queries"], ["SELECT '/tmp/home'"])


if __name__ == "__main__":
    unittest.main()
