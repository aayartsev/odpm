"""Tests for ODPM_PORT_OFFSET host published-port shifting."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.compose.compose_document import build_compose_document
from dev_project.compose.ports import (
    apply_host_port_offset,
    assert_host_port_in_range,
    parse_port_offset,
    shift_published_port_spec,
)
from dev_project.compose.validate import validate_compose_document
from dev_project.errors import ConfigError
from dev_project.host.ports import (
    effective_debugger_port,
    effective_odoo_port,
    effective_postgres_port,
)
from tests.fixtures.compose.golden_scenario_env import GOLDEN_PROJECT_DIR
from tests.test_compose_service_prefix import _make_compose_env


class ParsePortOffsetTests(unittest.TestCase):
    def test_empty_is_zero(self):
        self.assertEqual(parse_port_offset(None), 0)
        self.assertEqual(parse_port_offset(""), 0)
        self.assertEqual(parse_port_offset("  "), 0)

    def test_parses_signed_int(self):
        self.assertEqual(parse_port_offset("10"), 10)
        self.assertEqual(parse_port_offset("-5"), -5)

    def test_invalid_warns_and_returns_zero(self):
        with self.assertLogs("dev_project.compose.ports", level="WARNING"):
            self.assertEqual(parse_port_offset("nope"), 0)


class ShiftPublishedPortSpecTests(unittest.TestCase):
    def test_host_container(self):
        self.assertEqual(shift_published_port_spec("8069:8069", 10), "8079:8069")

    def test_ip_host_container(self):
        self.assertEqual(
            shift_published_port_spec("127.0.0.1:5432:5432", 10),
            "127.0.0.1:5442:5432",
        )

    def test_proto_suffix(self):
        self.assertEqual(shift_published_port_spec("8025:8025/tcp", 10), "8035:8025/tcp")

    def test_dict_published(self):
        self.assertEqual(
            shift_published_port_spec({"published": 8025, "target": 8025}, 10),
            {"published": 8035, "target": 8025},
        )

    def test_bare_container_unchanged(self):
        with self.assertLogs("dev_project.compose.ports", level="WARNING"):
            self.assertEqual(shift_published_port_spec("8025", 10), "8025")

    def test_ipv6_unchanged(self):
        with self.assertLogs("dev_project.compose.ports", level="WARNING"):
            self.assertEqual(
                shift_published_port_spec("[::1]:8069:8069", 10), "[::1]:8069:8069"
            )

    def test_out_of_range_raises(self):
        with self.assertRaises(ConfigError):
            shift_published_port_spec("65530:8069", 20)


class EffectivePortTests(unittest.TestCase):
    def test_adds_offset(self):
        user_env = MagicMock()
        user_env.odoo_port = 8069
        user_env.postgres_port = 5432
        user_env.debugger_port = 5678
        user_env.port_offset = 10
        self.assertEqual(effective_odoo_port(user_env), 8079)
        self.assertEqual(effective_postgres_port(user_env), 5442)
        self.assertEqual(effective_debugger_port(user_env), 5688)

    def test_out_of_range_raises(self):
        user_env = MagicMock()
        user_env.odoo_port = 65530
        user_env.port_offset = 20
        with self.assertRaises(ConfigError):
            effective_odoo_port(user_env)

    def test_assert_shared_helper(self):
        self.assertEqual(assert_host_port_in_range(80, context="t"), 80)
        with self.assertRaises(ConfigError):
            assert_host_port_in_range(0, context="t")


class ApplyHostPortOffsetDocumentTests(unittest.TestCase):
    def test_build_compose_document_offsets_odoo_db_and_sidecar(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        env = _make_compose_env(
            port_offset=10,
            manifest_services={
                "mailpit": {
                    "image": "axllent/mailpit",
                    "ports": ["8025:8025", "1025:1025"],
                }
            },
        )
        document = build_compose_document(env)
        validate_compose_document(document)
        odoo_ports = document["services"]["odoo"]["ports"]
        self.assertIn("8079:8069", odoo_ports)
        self.assertIn("8082:8072", odoo_ports)
        self.assertIn("5688:5678", odoo_ports)
        db_ports = document["services"]["db"]["ports"]
        self.assertTrue(any(p.endswith("15442:5432") or p == "15442:5432" for p in db_ports))
        mailpit_ports = document["services"]["mailpit"]["ports"]
        self.assertIn("8035:8025", mailpit_ports)
        self.assertIn("1035:1025", mailpit_ports)

    def test_offset_before_localhost_bind_preserves_ip(self):
        from dev_project.scenario_policy import format_published_port

        services = {"db": {"ports": ["127.0.0.1:5432:5432"]}}
        apply_host_port_offset(services, 10)
        self.assertEqual(services["db"]["ports"], ["127.0.0.1:5442:5432"])
        services["db"]["ports"] = [
            format_published_port(p) for p in services["db"]["ports"]
        ]
        self.assertEqual(services["db"]["ports"], ["127.0.0.1:5442:5432"])

    def test_offset_zero_noop(self):
        services = {"odoo": {"ports": ["8069:8069"]}}
        apply_host_port_offset(services, 0)
        self.assertEqual(services["odoo"]["ports"], ["8069:8069"])


if __name__ == "__main__":
    unittest.main()
