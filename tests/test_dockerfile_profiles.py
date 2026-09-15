"""Tests for scenario base Dockerfile profile resolution."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config.paths import ConfigPaths
from dev_project.dockerfile_profiles import (
    dockerfile_template_stem,
    parse_base_image_profile,
    resolve_base_image_profile,
    resolve_dockerfile_template_name,
)
from dev_project.host.user_env_parse import parse_dotenv_dict
from dev_project.scenario_policy import ScenarioPolicy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRAM_DIR = str(PROJECT_ROOT)


def _minimal_env_dict(**extra: str) -> dict[str, str]:
    data = {
        "BACKUP_DIR": "/tmp/backups",
        "ODOO_PROJECTS_DIR": "/tmp/projects",
        "PATH_TO_SSH_KEY": "",
        "ODOO_PORT": "8069",
        "POSTGRES_PORT": "5432",
        "DEBUGGER_PORT": "5678",
        "GEVENT_PORT": "8072",
        "ODPM_SCENARIO": constants.CI_SCENARIO,
    }
    data.update(extra)
    return data


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

    def test_ci_scenario_override_to_medium(self):
        policy = ScenarioPolicy.from_scenario(
            constants.CI_SCENARIO, base_image_profile="medium"
        )
        self.assertEqual(policy.scenario, constants.CI_SCENARIO)
        self.assertEqual(policy.base_image_profile, "medium")
        self.assertTrue(policy.allow_build_image)
        self.assertFalse(policy.include_odoo_volumes)

    def test_developer_override_to_ci(self):
        policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO, base_image_profile="ci"
        )
        self.assertEqual(policy.base_image_profile, "ci")
        self.assertTrue(policy.include_debugpy)


class ParseBaseImageProfileTests(unittest.TestCase):
    def test_unset_and_blank(self):
        self.assertIsNone(parse_base_image_profile(None))
        self.assertIsNone(parse_base_image_profile(""))
        self.assertIsNone(parse_base_image_profile("  "))

    def test_valid_profiles_normalized(self):
        self.assertEqual(parse_base_image_profile("FULL"), "full")
        self.assertEqual(parse_base_image_profile("medium"), "medium")
        self.assertEqual(parse_base_image_profile("ci"), "ci")

    def test_invalid_falls_back_with_warning(self):
        with self.assertLogs("dev_project.dockerfile_profiles", level="WARNING") as logs:
            self.assertIsNone(parse_base_image_profile("fat"))
        self.assertTrue(any("ODPM_BASE_IMAGE_PROFILE" in line for line in logs.output))

    def test_resolve_override_wins(self):
        self.assertEqual(
            resolve_base_image_profile("ci", override="medium"),
            "medium",
        )
        self.assertEqual(resolve_base_image_profile("ci", override=None), "ci")


class DotenvBaseImageProfileTests(unittest.TestCase):
    def test_parse_dotenv_reads_profile_override(self):
        env = _minimal_env_dict(ODPM_BASE_IMAGE_PROFILE="medium")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(constants.ODPM_BASE_IMAGE_PROFILE_ENV, None)
            parsed = parse_dotenv_dict(env)
        self.assertEqual(parsed.base_image_profile, "medium")
        self.assertEqual(parsed.odpm_scenario, constants.CI_SCENARIO)

    def test_process_env_wins_over_dotenv(self):
        env = _minimal_env_dict(ODPM_BASE_IMAGE_PROFILE="medium")
        with patch.dict(
            os.environ,
            {constants.ODPM_BASE_IMAGE_PROFILE_ENV: "full"},
            clear=False,
        ):
            parsed = parse_dotenv_dict(env)
        self.assertEqual(parsed.base_image_profile, "full")


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

    def test_odoo_image_name_uses_overridden_profile_suffix(self):
        config = MagicMock()
        config.arch = "amd64"
        config.python_version = "3.12"
        config.distro_name = "debian"
        config.distro_version = "12"
        config.policy = ScenarioPolicy.from_scenario(
            constants.CI_SCENARIO, base_image_profile="medium"
        )
        config.docker_layout = MagicMock()
        config.arguments = MagicMock(image_tag=None)
        config.odoo_version = "17.0"
        config.platform_name = "odoo"
        ConfigPaths(config).apply_image_names()
        self.assertTrue(config.docker_layout.odoo_image_name.endswith("-medium"))
