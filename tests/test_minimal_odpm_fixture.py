"""Unit tests for minimal odpm project fixture provisioning."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project


class MinimalOdpmFixtureTests(unittest.TestCase):
    def test_provision_creates_expected_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = provision_minimal_odpm_project(Path(tmp) / "project")

            self.assertTrue((project_dir / ".env").is_file())
            self.assertTrue((project_dir / "user_settings.json").is_file())
            self.assertTrue(
                (
                    project_dir
                    / constants.PROJECT_SERVICE_DIRECTORY
                    / "docker-compose.yml"
                ).is_file()
            )
            self.assertTrue(
                (project_dir / constants.ODPM_RUNTIME_DIR_REL_PATH / "config.json").is_file()
            )

            developing = project_dir / "developing"
            platform = project_dir / "platform" / "odoo"
            self.assertTrue((developing / "odpm.json").is_file())
            self.assertTrue((platform / "requirements.txt").is_file())
            self.assertTrue((platform / "odoo-bin").is_file())

            user_settings = json.loads(
                (project_dir / "user_settings.json").read_text(encoding="utf-8")
            )
            odpm_json = json.loads(
                (developing / "odpm.json").read_text(encoding="utf-8")
            )

            self.assertEqual(user_settings["developing_project"], developing.as_uri())
            self.assertEqual(odpm_json["odoo_git_link"], platform.as_uri())
            self.assertEqual(odpm_json["odpm_version"], constants.ODPM_VERSION)
            self.assertFalse(user_settings["check_system"])
            self.assertFalse(user_settings["create_module_links"])


if __name__ == "__main__":
    unittest.main()
