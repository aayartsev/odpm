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

    def test_hostname_and_healthcheck_pass_when_valid(self):
        validate_compose_document(
            {
                "services": {
                    "minio": {
                        "image": "minio/minio:latest",
                        "hostname": "minio",
                        "healthcheck": {
                            "test": ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"],
                            "interval": "30s",
                            "retries": 3,
                        },
                    }
                }
            }
        )

    def test_invalid_hostname_or_healthcheck_raises(self):
        with self.assertRaises(ConfigError):
            validate_compose_document(
                {"services": {"odoo": {"image": "odoo:dev", "hostname": ""}}}
            )
        with self.assertRaises(ConfigError):
            validate_compose_document(
                {"services": {"odoo": {"image": "odoo:dev", "healthcheck": "bad"}}}
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

    def test_undeclared_service_network_raises(self):
        with self.assertRaises(ConfigError):
            validate_compose_document(
                {
                    "services": {
                        "odoo": {
                            "image": "odoo:dev",
                            "networks": ["missing"],
                        }
                    },
                    "networks": {"stack": {"driver": "bridge"}},
                }
            )

    def test_declared_service_network_passes(self):
        validate_compose_document(
            {
                "services": {
                    "odoo": {
                        "image": "odoo:dev",
                        "networks": ["stack"],
                    }
                },
                "networks": {"stack": {"driver": "bridge"}},
            }
        )


if __name__ == "__main__":
    unittest.main()
