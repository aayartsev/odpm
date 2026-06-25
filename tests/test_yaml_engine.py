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

    def test_dump_nested_sequences_indent_for_compose_cli(self):
        text = dump_document(
            {
                "db": {
                    "image": "postgres:16",
                    "ports": ["15432:5432"],
                    "environment": ["POSTGRES_PASSWORD=odoo"],
                }
            }
        )
        self.assertIn("  ports:\n    - 15432:5432", text)
        self.assertIn("  environment:\n    - POSTGRES_PASSWORD=odoo", text)
        self.assertNotIn("  ports:\n  - ", text)

    def test_merge_services_preserves_base_order_and_replaces_overlay_names(self):
        base = {
            "db": {"image": "postgres:16"},
            "odoo": {"image": "odoo:dev", "ports": ["8069:8069"]},
        }
        overlay = {
            "mailpit": {"image": "plugin/mailpit:latest"},
        }
        merged = merge_services(base, overlay)
        self.assertEqual(list(merged.keys()), ["db", "odoo", "mailpit"])
        self.assertEqual(merged["odoo"]["image"], "odoo:dev")
        self.assertEqual(merged["mailpit"], {"image": "plugin/mailpit:latest"})

    def test_merge_services_with_patches_appends_environment(self):
        from dev_project.yaml import merge_services_with_patches

        services = {
            "odoo": {
                "image": "odoo:dev",
                "environment": ["PYTHONUNBUFFERED=1"],
            }
        }
        patched = merge_services_with_patches(
            services,
            {"odoo": {"environment": {"EXTRA_FLAG": "1"}}},
        )
        self.assertIn("PYTHONUNBUFFERED=1", patched["odoo"]["environment"])
        self.assertIn("EXTRA_FLAG=1", patched["odoo"]["environment"])

    def test_merge_services_with_patches_replaces_ports_list(self):
        from dev_project.yaml import merge_services_with_patches

        services = {"odoo": {"ports": ["8069:8069", "8072:8072"]}}
        patched = merge_services_with_patches(
            services, {"odoo": {"ports": ["9090:8069"]}}
        )
        self.assertEqual(patched["odoo"]["ports"], ["9090:8069"])

    def test_merge_services_with_patches_unknown_service_raises(self):
        from dev_project.yaml import merge_services_with_patches

        with self.assertRaises(ValueError):
            merge_services_with_patches({"odoo": {}}, {"redis": {"image": "redis"}})

    def test_dump_renders_exec_form_command(self):
        text = dump_document(
            {
                "sidecar": {
                    "image": "busybox:latest",
                    "command": ["sh", "-c", "sleep", "infinity"],
                }
            }
        )
        self.assertIn("command:", text)
        self.assertIn("- sh", text)

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
