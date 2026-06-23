"""Tests for compose document validation (D5-1)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dev_project.compose.validate import (
    validate_compose_document,
    validate_compose_file,
    validate_compose_text,
)
from dev_project.errors import ConfigError
from dev_project.yaml import dump_document


class ComposeValidateTests(unittest.TestCase):
    def test_valid_minimal_document_passes(self):
        validate_compose_document(
            {
                "services": {
                    "odoo": {
                        "image": "odoo:dev",
                        "command": ["python3", "-m", "odpm"],
                    }
                }
            }
        )

    def test_missing_services_raises(self):
        with self.assertRaises(ConfigError):
            validate_compose_document({})

    def test_service_without_image_raises(self):
        with self.assertRaises(ConfigError):
            validate_compose_document({"services": {"odoo": {"ports": ["8069:8069"]}}})

    def test_non_list_ports_raises(self):
        with self.assertRaises(ConfigError):
            validate_compose_document(
                {"services": {"odoo": {"image": "odoo:dev", "ports": "8069:8069"}}}
            )

    def test_invalid_user_or_tty_raises(self):
        with self.assertRaises(ConfigError):
            validate_compose_document(
                {"services": {"odoo": {"image": "odoo:dev", "user": ""}}}
            )
        with self.assertRaises(ConfigError):
            validate_compose_document(
                {"services": {"odoo": {"image": "odoo:dev", "tty": "yes"}}}
            )

    def test_user_and_tty_pass_when_valid(self):
        validate_compose_document(
            {
                "services": {
                    "sidecar": {
                        "image": "busybox:latest",
                        "user": "root",
                        "tty": True,
                    }
                }
            }
        )

    def test_validate_text_skips_header_comment(self):
        body = dump_document({"services": {"db": {"image": "postgres:16"}}})
        validate_compose_text(f"# generated\n\n{body}")

    def test_validate_file_reads_disk_compose(self):
        body = dump_document({"services": {"odoo": {"image": "odoo:dev"}}})
        with tempfile.TemporaryDirectory() as project_dir:
            path = Path(project_dir) / "docker-compose.yml"
            path.write_text(f"# hdr\n\n{body}", encoding="utf-8")
            validate_compose_file(str(path))

    def test_validate_file_missing_raises(self):
        with self.assertRaises(ConfigError):
            validate_compose_file("/nonexistent/docker-compose.yml")


if __name__ == "__main__":
    unittest.main()
