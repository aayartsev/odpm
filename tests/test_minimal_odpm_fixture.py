"""Unit tests for minimal odpm project fixture provisioning."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from tests.fixtures.minimal_odpm_fixture import (
    build_v2_manifest_with_mailpit,
    provision_minimal_odpm_project,
)
from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_NAME


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
            self.assertEqual(odpm_json["odpm_version"], constants.MANIFEST_V1_CONTRACT_LINE)
            self.assertFalse(user_settings["check_system"])
            self.assertFalse(user_settings["create_module_links"])

    def test_provision_v2_mailpit_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = provision_minimal_odpm_project(
                Path(tmp) / "project",
                manifest_v2_mailpit=True,
            )
            developing = project_dir / "developing"
            platform = project_dir / "platform" / "odoo"
            odpm_json = json.loads(
                (developing / "odpm.json").read_text(encoding="utf-8")
            )
            self.assertEqual(odpm_json["manifest_schema"], constants.MANIFEST_SCHEMA_V2)
            self.assertEqual(
                odpm_json["services"][MAILPIT_SERVICE_NAME]["image"],
                "axllent/mailpit",
            )
            self.assertEqual(odpm_json["platform"]["git"], platform.as_uri())
            self.assertEqual(odpm_json["developing"]["git"], developing.as_uri())

    def test_provision_scenario_ci_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = provision_minimal_odpm_project(
                Path(tmp) / "project",
                scenario=constants.CI_SCENARIO,
            )
            env_text = (project_dir / ".env").read_text(encoding="utf-8")
            self.assertIn(f"ODPM_SCENARIO={constants.CI_SCENARIO}", env_text)

    def test_provision_locks_drift_seeds_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = provision_minimal_odpm_project(
                Path(tmp) / "project",
                manifest_v2_mailpit=True,
                locks_drift=True,
            )
            odpm_json = json.loads(
                (project_dir / "developing" / "odpm.json").read_text(encoding="utf-8")
            )
            lock_json = json.loads(
                (
                    project_dir / constants.DEPS_LOCK_REL_PATH
                ).read_text(encoding="utf-8")
            )
            manifest_commit = odpm_json["locks"]["git"][
                (project_dir / "platform" / "odoo").as_uri()
            ]
            file_commit = lock_json["platform"]["commit"]
            self.assertNotEqual(manifest_commit, file_commit)

    def test_build_v2_manifest_with_mailpit_helper(self) -> None:
        flat = {
            "odoo_version": "17.0",
            "python_version": "3.12",
            "distro_name": "debian",
            "distro_version": "12",
            "postgres_version": "16",
            "dependencies": [],
            "requirements_txt": [],
        }
        manifest = build_v2_manifest_with_mailpit(
            platform_uri="file:///platform",
            developing_uri="file:///developing",
            flat=flat,
        )
        self.assertEqual(manifest["manifest_schema"], 2)
        self.assertIn(MAILPIT_SERVICE_NAME, manifest["services"])


if __name__ == "__main__":
    unittest.main()
