"""Tests for ODPM_COMPOSE_PREFIX and compose naming context (4.7 B0)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project.compose.service_names import (
    LOGICAL_ODOO,
    LOGICAL_POSTGRES_VOLUME,
    compose_project_name_from_prefix,
    parse_compose_prefix,
    resolve_compose_naming,
)
from dev_project.host.user_env import CreateUserEnvironment
from tests.test_noninteractive_init import _make_pd_manager


class ComposePrefixParseTests(unittest.TestCase):
    def test_empty_prefix_disabled(self):
        self.assertIsNone(parse_compose_prefix(None))
        self.assertIsNone(parse_compose_prefix(""))
        self.assertIsNone(parse_compose_prefix("   "))

    def test_normalizes_trailing_dash(self):
        self.assertEqual(parse_compose_prefix("acme"), "acme-")
        self.assertEqual(parse_compose_prefix("acme-"), "acme-")
        self.assertEqual(parse_compose_prefix("  Foo-Bar  "), "foo-bar-")

    def test_rejects_invalid_prefix(self):
        self.assertIsNone(parse_compose_prefix("-acme"))
        self.assertIsNone(parse_compose_prefix("acme.db"))
        self.assertIsNone(parse_compose_prefix("acme_1"))


class ComposeNamingContextTests(unittest.TestCase):
    def test_legacy_without_prefix(self):
        ctx = resolve_compose_naming(
            compose_prefix_raw=None,
            legacy_postgres_service_name="pg-dev",
        )
        self.assertFalse(ctx.uses_prefix)
        self.assertIsNone(ctx.compose_prefix)
        self.assertIsNone(ctx.compose_project_name)
        self.assertEqual(ctx.postgres_service_name, "pg-dev")
        self.assertEqual(ctx.odoo_service_name, LOGICAL_ODOO)
        self.assertEqual(ctx.postgres_volume_name, LOGICAL_POSTGRES_VOLUME)

    def test_prefix_derives_full_stack_names(self):
        ctx = resolve_compose_naming(
            compose_prefix_raw="acme",
            legacy_postgres_service_name="db",
        )
        self.assertTrue(ctx.uses_prefix)
        self.assertEqual(ctx.compose_prefix, "acme-")
        self.assertEqual(ctx.compose_project_name, "acme")
        self.assertEqual(ctx.postgres_service_name, "acme-db")
        self.assertEqual(ctx.odoo_service_name, "acme-odoo")
        self.assertEqual(ctx.postgres_volume_name, "acme-postgres-data")

    def test_prefix_warns_when_legacy_postgres_overridden(self):
        with self.assertLogs("dev_project.compose.service_names", level="WARNING") as logs:
            ctx = resolve_compose_naming(
                compose_prefix_raw="acme",
                legacy_postgres_service_name="postgres",
            )
        self.assertEqual(ctx.postgres_service_name, "acme-db")
        self.assertTrue(any("POSTGRES_SERVICE_NAME" in msg for msg in logs.output))

    def test_compose_project_name_strips_trailing_dash(self):
        self.assertEqual(compose_project_name_from_prefix("foo-bar-"), "foo-bar")


class ComposePrefixUserEnvTests(unittest.TestCase):
    @patch("dev_project.host.user_env._stdin_is_interactive", return_value=False)
    def test_reads_compose_prefix_from_project_env(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = Path(project_dir) / ".env"
            project_env.write_text(
                "\n".join(
                    [
                        "BACKUP_DIR=/tmp/backups",
                        "ODOO_PROJECTS_DIR=/tmp/projects",
                        "PATH_TO_SSH_KEY=",
                        "ODOO_PORT=8069",
                        "POSTGRES_PORT=5432",
                        "DEBUGGER_PORT=5678",
                        "GEVENT_PORT=8072",
                        "ODPM_SCENARIO=developer",
                        "ODPM_COMPOSE_PREFIX=acme",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                user_env = CreateUserEnvironment(_make_pd_manager(project_dir, home_dir=home_dir))
            self.assertEqual(user_env.compose_prefix, "acme-")
            self.assertEqual(user_env.compose_project_name, "acme")
            self.assertEqual(user_env.postgres_service_name, "acme-db")
            self.assertEqual(user_env.odoo_service_name, "acme-odoo")
            self.assertEqual(user_env.postgres_volume_name, "acme-postgres-data")
            from dev_project.config.transforms.env_substitution import (
                EnvResolver,
                expand_env_string,
            )

            resolver = EnvResolver.from_user_env(user_env, process_environ={})
            self.assertEqual(
                expand_env_string(
                    "${@service:db}",
                    resolver,
                    field_path="services.sidecar.environment.DB_HOST",
                ),
                "acme-db",
            )

    @patch("dev_project.host.user_env._stdin_is_interactive", return_value=False)
    def test_legacy_postgres_name_when_prefix_absent(self, _mock_tty):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            project_env = Path(project_dir) / ".env"
            project_env.write_text(
                "\n".join(
                    [
                        "BACKUP_DIR=/tmp/backups",
                        "ODOO_PROJECTS_DIR=/tmp/projects",
                        "PATH_TO_SSH_KEY=",
                        "ODOO_PORT=8069",
                        "POSTGRES_PORT=5432",
                        "POSTGRES_SERVICE_NAME=postgres",
                        "DEBUGGER_PORT=5678",
                        "GEVENT_PORT=8072",
                        "ODPM_SCENARIO=developer",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"HOME": home_dir}, clear=True):
                user_env = CreateUserEnvironment(_make_pd_manager(project_dir, home_dir=home_dir))
            self.assertIsNone(user_env.compose_prefix)
            self.assertEqual(user_env.postgres_service_name, "postgres")
            self.assertEqual(user_env.odoo_service_name, "odoo")


if __name__ == "__main__":
    unittest.main()
