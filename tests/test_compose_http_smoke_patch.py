"""Unit tests for HTTP smoke compose port patching."""

from __future__ import annotations

import unittest

from tests.integration.compose_http_smoke_patch import patch_mailpit_service_ports


class ComposeHttpSmokePatchTests(unittest.TestCase):
    def test_patch_mailpit_ports_remaps_host_bindings(self):
        source = """services:
  mailpit:
    image: axllent/mailpit
    ports:
    - 8025:8025
    - 1025:1025
"""
        patched = patch_mailpit_service_ports(
            source, ui_port=18025, smtp_port=11025, service_name="mailpit"
        )
        self.assertIn("    - 18025:8025", patched)
        self.assertIn("    - 11025:1025", patched)
        self.assertNotIn("    - 8025:8025", patched)

    def test_patch_mailpit_ports_skips_ruamel_sequence_indent(self):
        source = """services:
  mailpit:
    image: axllent/mailpit
    ports:
      - 8025:8025
      - 1025:1025
"""
        patched = patch_mailpit_service_ports(
            source, ui_port=18025, smtp_port=11025, service_name="mailpit"
        )
        self.assertIn("    - 18025:8025", patched)
        self.assertIn("    - 11025:1025", patched)
        self.assertNotIn("    - 8025:8025", patched)
        self.assertNotIn("      - 8025:8025", patched)


if __name__ == "__main__":
    unittest.main()
