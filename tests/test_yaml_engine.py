"""Tests for host YAML engine (ADR-005)."""

from __future__ import annotations

import unittest

from dev_project.yaml import dump_document, load_document, merge_services


class YamlEngineTests(unittest.TestCase):
    def test_round_trip_simple_mapping(self):
        document = {"services": {"mailpit": {"image": "axllent/mailpit"}}}
        loaded = load_document(dump_document(document))
        self.assertEqual(loaded, document)

    def test_dump_quotes_numeric_command_tokens(self):
        text = dump_document({"command": ["python3", "99999", "true"]})
        self.assertIn('- "99999"', text)
        self.assertIn('- "true"', text)
        self.assertIn("- python3", text)

    def test_merge_services_preserves_base_order_and_appends_extras(self):
        base = {
            "db": {"image": "postgres:16"},
            "odoo": {"image": "odoo:dev"},
        }
        overlay = {
            "mailpit": {"image": "axllent/mailpit"},
            "odoo": {"ports": ["8025:8025"]},
        }
        merged = merge_services(base, overlay)
        self.assertEqual(list(merged.keys()), ["db", "odoo", "mailpit"])
        self.assertEqual(merged["odoo"], {"ports": ["8025:8025"]})

    def test_render_compose_services_block_via_engine(self):
        from dev_project.compose.fragments import render_compose_services_block

        block = render_compose_services_block(
            {"mailpit": {"image": "axllent/mailpit", "ports": ["8025:8025"]}}
        )
        self.assertIn("  mailpit:", block)
        self.assertIn("    image: axllent/mailpit", block)
        self.assertIn("    ports:", block)
        self.assertIn("      - 8025:8025", block)


if __name__ == "__main__":
    unittest.main()
