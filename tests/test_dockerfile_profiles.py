"""Tests for scenario base Dockerfile profile resolution."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.config.paths import ConfigPaths
from dev_project.dockerfile_profiles import (
    dockerfile_template_stem,
    resolve_dockerfile_template_name,
)
from dev_project.scenario_policy import ScenarioPolicy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRAM_DIR = str(PROJECT_ROOT)


class DockerfileProfileResolutionTests(unittest.TestCase):
    def test_stem_normalizes_distro_version(self):
        self.assertEqual(dockerfile_template_stem("debian", "12"), "debian_12_dockerfile")

    def test_resolve_debian_12_ci_profile(self):
        name = resolve_dockerfile_template_name(
            PROGRAM_DIR, "debian", "12", "ci"
        )
        self.assertEqual(name, "debian_12_dockerfile_ci")

    def test_resolve_debian_12_full_profile(self):
        name = resolve_dockerfile_template_name(
            PROGRAM_DIR, "debian", "12", "full"
        )
        self.assertEqual(name, "debian_12_dockerfile_full")

    def test_resolve_legacy_distro_without_profiles(self):
        name = resolve_dockerfile_template_name(
            PROGRAM_DIR, "ubuntu", "20.04", "ci"
        )
        self.assertEqual(name, "ubuntu_2004_dockerfile")

    def test_ci_template_excludes_browser_stack(self):
        template = (
            PROJECT_ROOT
            / "dev_project"
            / "templates"
            / "debian_12_dockerfile_ci"
        ).read_text(encoding="utf-8")
        self.assertNotIn("chromium", template)
        self.assertNotIn(".vscode-server", template)
        self.assertNotIn("wkhtmltox", template)

    def test_medium_template_excludes_browser_keeps_wkhtmltopdf(self):
        template = (
            PROJECT_ROOT
            / "dev_project"
            / "templates"
            / "debian_12_dockerfile_medium"
        ).read_text(encoding="utf-8")
        self.assertNotIn("chromium", template)
        self.assertNotIn(".vscode-server", template)
        self.assertIn("wkhtmltox", template)

    def test_full_template_includes_developer_stack(self):
        template = (
            PROJECT_ROOT
            / "dev_project"
            / "templates"
            / "debian_12_dockerfile_full"
        ).read_text(encoding="utf-8")
        self.assertIn("chromium", template)
        self.assertIn(".vscode-server", template)


class ScenarioPolicyProfileTests(unittest.TestCase):
    def test_developer_uses_full_profile(self):
        policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        self.assertEqual(policy.base_image_profile, "full")

    def test_server_uses_medium_profile(self):
        policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        self.assertEqual(policy.base_image_profile, "medium")

    def test_ci_uses_ci_profile(self):
        policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        self.assertEqual(policy.base_image_profile, "ci")


class ImageNameProfileSuffixTests(unittest.TestCase):
    def test_odoo_image_name_includes_profile_suffix(self):
        config = MagicMock()
        config.arch = "amd64"
        config.python_version = "3.12"
        config.distro_name = "debian"
        config.distro_version = "12"
        config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        config.docker_layout = MagicMock()
        config.arguments = MagicMock(image_tag=None)
        config.odoo_version = "17.0"
        config.platform_name = "odoo"
        ConfigPaths(config).apply_image_names()
        self.assertTrue(config.docker_layout.odoo_image_name.endswith("-ci"))
