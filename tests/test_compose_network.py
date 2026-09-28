"""Tests for ODPM_COMPOSE_NETWORK parse and ComposeNetworkContext (4.7 D1–D2)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project import constants
from dev_project.compose.compose_document import build_compose_document
from dev_project.compose.network_names import (
    LOGICAL_STACK_NETWORK,
    ComposeNetworkContext,
    apply_compose_network,
    attach_logical_compose_network,
    compose_network_from_user_env,
    parse_compose_network_external,
    parse_compose_network_name,
    resolve_compose_network,
)
from dev_project.compose.service_names import (
    LOGICAL_DB,
    LOGICAL_ODOO,
    apply_compose_physical_names,
    resolve_compose_naming,
)
from dev_project.compose.validate import validate_compose_document
from dev_project.host.user_env import CreateUserEnvironment
from tests.test_compose_service_prefix import _make_compose_env
from tests.test_noninteractive_init import _make_pd_manager
from tests.fixtures.compose.golden_scenario_env import GOLDEN_PROJECT_DIR

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


class AttachComposeNetworkTests(unittest.TestCase):
    def test_attach_managed_network_to_services_without_networks(self):
        document = {
            "services": {
                LOGICAL_DB: {"image": "postgres:16"},
                LOGICAL_ODOO: {"image": "odoo:dev", "depends_on": [LOGICAL_DB]},
            }
        }
        net_ctx = ComposeNetworkContext(
            logical_name="stack",
            physical_name="stack",
            external=False,
        )
        attach_logical_compose_network(document, net_ctx)
        self.assertEqual(document["networks"], {"stack": {"driver": "bridge"}})
        self.assertEqual(document["services"][LOGICAL_DB]["networks"], ["stack"])
        self.assertEqual(document["services"][LOGICAL_ODOO]["networks"], ["stack"])

    def test_attach_skips_service_with_existing_networks(self):
        document = {
            "services": {
                LOGICAL_DB: {"image": "postgres:16"},
                "mailpit": {"image": "axllent/mailpit", "networks": ["proxy"]},
            }
        }
        net_ctx = ComposeNetworkContext(
            logical_name="stack",
            physical_name="stack",
            external=False,
        )
        attach_logical_compose_network(document, net_ctx)
        self.assertEqual(document["services"][LOGICAL_DB]["networks"], ["stack"])
        self.assertEqual(document["services"]["mailpit"]["networks"], ["proxy"])


class ApplyComposeNetworkTests(unittest.TestCase):
    def test_apply_rewrites_managed_network_with_prefix(self):
        document = {
            "services": {
                "db": {"image": "postgres:16", "networks": ["stack"]},
                "odoo": {"image": "odoo:dev", "networks": ["stack"]},
                "mailpit": {
                    "image": "axllent/mailpit",
                    "networks": ["stack"],
                    "depends_on": ["db"],
                },
            },
            "networks": {"stack": {"driver": "bridge"}},
        }
        naming = resolve_compose_naming(
            compose_prefix_raw="acme",
            legacy_postgres_service_name=constants.DEFAULT_POSTGRES_SERVICE_NAME,
        )
        net_ctx = resolve_compose_network(
            network_raw="stack",
            external_raw=None,
            naming=naming,
        )
        apply_compose_physical_names(
            document,
            naming,
            network_ctx=net_ctx,
        )
        self.assertEqual(document["networks"], {"acme-stack": {"driver": "bridge"}})
        self.assertEqual(document["services"]["acme-db"]["networks"], ["acme-stack"])
        self.assertEqual(document["services"]["mailpit"]["networks"], ["acme-stack"])
        validate_compose_document(document)

    def test_apply_external_network_keeps_name_with_prefix(self):
        document = {
            "services": {
                LOGICAL_DB: {"image": "postgres:16", "networks": ["proxy"]},
                LOGICAL_ODOO: {"image": "odoo:dev", "networks": ["proxy"]},
            },
            "networks": {"proxy": {"external": True}},
        }
        naming = resolve_compose_naming(
            compose_prefix_raw="acme",
            legacy_postgres_service_name=constants.DEFAULT_POSTGRES_SERVICE_NAME,
        )
        net_ctx = resolve_compose_network(
            network_raw="proxy",
            external_raw="1",
            naming=naming,
        )
        apply_compose_network(document, net_ctx, naming)
        self.assertEqual(document["networks"], {"proxy": {"external": True}})
        self.assertEqual(document["services"][LOGICAL_DB]["networks"], ["proxy"])
        validate_compose_document(document)


class BuildComposeDocumentNetworkTests(unittest.TestCase):
    def test_build_without_network_has_no_networks_section(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        document = build_compose_document(_make_compose_env())
        validate_compose_document(document)
        self.assertNotIn("networks", document)

    def test_build_managed_network_attaches_builtin_services(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        document = build_compose_document(
            _make_compose_env(
                compose_network_logical="stack",
                compose_network_physical="stack",
            )
        )
        validate_compose_document(document)
        self.assertEqual(document["networks"], {"stack": {"driver": "bridge"}})
        self.assertEqual(document["services"][LOGICAL_DB]["networks"], ["stack"])
        self.assertEqual(document["services"][LOGICAL_ODOO]["networks"], ["stack"])

    def test_build_external_network_with_prefix(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        document = build_compose_document(
            _make_compose_env(
                compose_prefix="acme",
                compose_network_logical="proxy",
                compose_network_physical="proxy",
                compose_network_external=True,
            )
        )
        validate_compose_document(document)
        self.assertEqual(document["networks"], {"proxy": {"external": True}})
        self.assertEqual(document["services"]["acme-db"]["networks"], ["proxy"])
        self.assertEqual(document["services"]["acme-odoo"]["networks"], ["proxy"])

    def test_build_prefix_and_managed_network_physical_name(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        document = build_compose_document(
            _make_compose_env(
                compose_prefix="acme",
                compose_network_logical="stack",
                compose_network_physical="acme-stack",
            )
        )
        validate_compose_document(document)
        self.assertEqual(document["networks"], {"acme-stack": {"driver": "bridge"}})
        self.assertEqual(document["services"]["acme-odoo"]["depends_on"], ["acme-db"])
        self.assertEqual(document["services"]["acme-db"]["networks"], ["acme-stack"])


if __name__ == "__main__":
    unittest.main()
