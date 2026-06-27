"""Tests for ODPM_COMPOSE_NETWORK parse and ComposeNetworkContext (4.7 D1)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project.compose.network_names import (
    LOGICAL_STACK_NETWORK,
    compose_network_from_user_env,
    parse_compose_network_external,
    parse_compose_network_name,
    resolve_compose_network,
)
from dev_project.compose.service_names import resolve_compose_naming
from dev_project.host.user_env import CreateUserEnvironment
from tests.test_noninteractive_init import _make_pd_manager

_ENV_LINES = [
    "BACKUP_DIR=/tmp/backups",
    "ODOO_PROJECTS_DIR=/tmp/projects",
    "PATH_TO_SSH_KEY=",
    "ODOO_PORT=8069",
    "POSTGRES_PORT=5432",
    "DEBUGGER_PORT=5678",
    "GEVENT_PORT=8072",
    "ODPM_SCENARIO=developer",
]


class ComposeNetworkParseTests(unittest.TestCase):
    def test_empty_network_disabled(self):
        self.assertIsNone(parse_compose_network_name(None))
        self.assertIsNone(parse_compose_network_name(""))
        self.assertIsNone(parse_compose_network_name("   "))

    def test_normalizes_network_name(self):
        self.assertEqual(parse_compose_network_name("stack"), "stack")
        self.assertEqual(parse_compose_network_name("Proxy"), "proxy")
        self.assertEqual(parse_compose_network_name("  foo-bar  "), "foo-bar")

    def test_rejects_invalid_network_name(self):
        self.assertIsNone(parse_compose_network_name("-proxy"))
        self.assertIsNone(parse_compose_network_name("proxy.net"))
        self.assertIsNone(parse_compose_network_name("proxy_net"))

    def test_external_truthy_values(self):
        self.assertTrue(parse_compose_network_external("1"))
        self.assertTrue(parse_compose_network_external("true"))
        self.assertTrue(parse_compose_network_external("YES"))

    def test_external_falsey_values(self):
        self.assertFalse(parse_compose_network_external(None))
        self.assertFalse(parse_compose_network_external(""))
        self.assertFalse(parse_compose_network_external("0"))
        self.assertFalse(parse_compose_network_external("false"))


class ComposeNetworkContextTests(unittest.TestCase):
    def test_unset_network_inactive(self):
        ctx = resolve_compose_network(
            network_raw=None,
            external_raw=None,
            naming=resolve_compose_naming(
                compose_prefix_raw=None,
                legacy_postgres_service_name="db",
            ),
        )
        self.assertFalse(ctx.is_active)
        self.assertIsNone(ctx.logical_name)
        self.assertIsNone(ctx.physical_name)
        self.assertFalse(ctx.external)

    def test_external_without_network_name_inactive(self):
        ctx = resolve_compose_network(
            network_raw=None,
            external_raw="1",
            naming=resolve_compose_naming(
                compose_prefix_raw="acme",
                legacy_postgres_service_name="db",
            ),
        )
        self.assertFalse(ctx.is_active)

    def test_managed_network_without_prefix(self):
        ctx = resolve_compose_network(
            network_raw="stack",
            external_raw=None,
            naming=resolve_compose_naming(
                compose_prefix_raw=None,
                legacy_postgres_service_name="db",
            ),
        )
        self.assertTrue(ctx.is_active)
        self.assertEqual(ctx.logical_name, LOGICAL_STACK_NETWORK)
        self.assertEqual(ctx.physical_name, "stack")
        self.assertFalse(ctx.external)

    def test_managed_network_with_prefix(self):
        ctx = resolve_compose_network(
            network_raw="stack",
            external_raw=None,
            naming=resolve_compose_naming(
                compose_prefix_raw="acme",
                legacy_postgres_service_name="db",
            ),
        )
        self.assertEqual(ctx.physical_name, "acme-stack")

    def test_external_network_ignores_prefix(self):
        ctx = resolve_compose_network(
            network_raw="proxy",
            external_raw="1",
            naming=resolve_compose_naming(
                compose_prefix_raw="acme",
                legacy_postgres_service_name="db",
            ),
        )
        self.assertTrue(ctx.external)
        self.assertEqual(ctx.logical_name, "proxy")
        self.assertEqual(ctx.physical_name, "proxy")

    def test_invalid_network_name_disables_context(self):
        with self.assertLogs("dev_project.compose.network_names", level="WARNING"):
            ctx = resolve_compose_network(
                network_raw="bad_name",
                external_raw=None,
                naming=resolve_compose_naming(
                    compose_prefix_raw=None,
                    legacy_postgres_service_name="db",
                ),
            )
        self.assertFalse(ctx.is_active)


class ComposeNetworkUserEnvTests(unittest.TestCase):
    @patch("dev_project.host.user_env._stdin_is_interactive", return_value=False)
    def test_reads_managed_network_from_project_env(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = Path(project_dir) / ".env"
            project_env.write_text(
                "\n".join([*_ENV_LINES, "ODPM_COMPOSE_NETWORK=stack"]) + "\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                user_env = CreateUserEnvironment(
                    _make_pd_manager(project_dir, home_dir=home_dir)
                )
            self.assertEqual(user_env.compose_network_logical, "stack")
            self.assertEqual(user_env.compose_network_physical, "stack")
            self.assertFalse(user_env.compose_network_external)
            ctx = compose_network_from_user_env(user_env)
            self.assertTrue(ctx.is_active)

    @patch("dev_project.host.user_env._stdin_is_interactive", return_value=False)
    def test_reads_external_network_with_prefix(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = Path(project_dir) / ".env"
            project_env.write_text(
                "\n".join(
                    [
                        *_ENV_LINES,
                        "ODPM_COMPOSE_PREFIX=acme",
                        "ODPM_COMPOSE_NETWORK=proxy",
                        "ODPM_COMPOSE_NETWORK_EXTERNAL=1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                user_env = CreateUserEnvironment(
                    _make_pd_manager(project_dir, home_dir=home_dir)
                )
            self.assertEqual(user_env.compose_network_logical, "proxy")
            self.assertEqual(user_env.compose_network_physical, "proxy")
            self.assertTrue(user_env.compose_network_external)

    @patch("dev_project.host.user_env._stdin_is_interactive", return_value=False)
    def test_network_absent_when_unset(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = Path(project_dir) / ".env"
            project_env.write_text("\n".join(_ENV_LINES) + "\n", encoding="utf-8")
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                user_env = CreateUserEnvironment(
                    _make_pd_manager(project_dir, home_dir=home_dir)
                )
            self.assertIsNone(user_env.compose_network_logical)
            self.assertIsNone(user_env.compose_network_physical)
            self.assertFalse(user_env.compose_network_external)


if __name__ == "__main__":
    unittest.main()
