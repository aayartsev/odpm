"""Unit tests for dev_mode → compose ``--dev`` wiring."""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

from dev_project.host.cli.args import OdpmCliArgs

from dev_project import constants
from dev_project.compose.service_builder import ComposeServiceBuilder
from dev_project.dev_mode import (
    dev_mode_disabled,
    effective_dev_mode,
    dev_mode_includes_reload,
    dev_mode_includes_xml,
    is_autoreload_requirement,
    iter_dev_mode_compose_cases,
    merge_autoreload_requirements,
)
from dev_project.scenario_policy import ScenarioPolicy


class DevModeHelperTests(unittest.TestCase):
    def test_dev_mode_disabled_values(self):
        for value in (False, None, "", "   "):
            with self.subTest(value=repr(value)):
                self.assertTrue(dev_mode_disabled(value))

    def test_dev_mode_enabled_values(self):
        for value in ("reload", "all", "reload,qweb"):
            with self.subTest(value=value):
                self.assertFalse(dev_mode_disabled(value))

    def test_dev_mode_includes_xml(self):
        cases = [
            (False, False),
            ("reload", False),
            ("xml", True),
            ("all", True),
            ("reload,qweb,werkzeug,xml", True),
            ("reload,qweb,werkzeug,access", False),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(dev_mode_includes_xml(value), expected)

    def test_dev_mode_includes_reload(self):
        cases = [
            (False, False),
            ("qweb", False),
            ("reload", True),
            ("all", True),
            ("reload,qweb", True),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(dev_mode_includes_reload(value), expected)

    def test_is_autoreload_requirement(self):
        self.assertTrue(is_autoreload_requirement("inotify"))
        self.assertTrue(is_autoreload_requirement("watchdog==3.0.0"))
        self.assertFalse(is_autoreload_requirement("requests"))

    def test_effective_dev_mode_respects_scenario_policy(self):
        self.assertFalse(
            effective_dev_mode("reload", apply_dev_mode=False),
        )
        self.assertEqual(
            effective_dev_mode("reload", apply_dev_mode=True),
            "reload",
        )

    def test_merge_autoreload_requirements(self):
        base = ["pre-commit", "requests==2.31.0"]
        self.assertEqual(
            merge_autoreload_requirements(base, False),
            base,
        )
        merged = merge_autoreload_requirements(base, "all")
        self.assertIn("inotify", merged)
        self.assertNotIn("watchdog==3.0.0", merged)
        self.assertEqual(
            merge_autoreload_requirements(base + ["watchdog==1.0"], "reload"),
            base + ["inotify"],
        )


class ComposeDevModeTests(unittest.TestCase):
    def _make_config(self, scenario: str = constants.DEVELOPER_SCENARIO):
        config = MagicMock()
        config.project_dir = "/tmp/odpm-test-project"
        config.user_env.odpm_scenario = scenario
        config.policy = ScenarioPolicy.from_scenario(scenario)
        config.container_run_mode = constants.RUN_MODE_ODOO
        config.arguments = OdpmCliArgs(
            d=None,
            translate=None,
            start_precommit=False,
            export_po_files=None,
            i=False,
            u=False,
            test=False,
            screencasts=False,
            odoo_bin=[],
        )
        config.dev_mode = False
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.docker_project_dir = "/home/odoo"
        config.docker_inside_app = "/home/odoo/dev_project/inside_docker_app"
        config.docker_venv_dir = "/home/odoo/.venv"
        config.platform_name = "odoo"
        config.odoo_version = "19.0"
        config.init_modules = ""
        config.update_modules = ""
        config.docker_odoo_project_dir_path = "/home/odoo/extra-addons/project"
        config.docker_temp_tests_dir = "/home/odoo/odoo_tests"
        config.requirements_txt = []
        config.config_to_json.return_value = b"{}"
        config.generate_odoo_conf_docker_data = MagicMock()
        return config

    def _dev_flag_from_command(self, command: list[str]) -> str | None:
        if "--dev" not in command:
            return None
        index = command.index("--dev")
        self.assertLess(index + 1, len(command), "missing value after --dev")
        return command[index + 1]

    @patch("dev_project.compose.service_builder.persist_runtime_config")
    def test_compose_dev_mode_matrix(self, _mock_write_runtime_config):
        for case_id, dev_mode_value, expected_argv in iter_dev_mode_compose_cases():
            with self.subTest(case_id=case_id, dev_mode=dev_mode_value):
                config = self._make_config()
                config.dev_mode = dev_mode_value
                ComposeServiceBuilder(config).build()
                actual = self._dev_flag_from_command(config.compose_service.command)
                self.assertEqual(actual, expected_argv)

    @patch("dev_project.compose.service_builder.persist_runtime_config")
    def test_dev_mode_applies_only_in_developer_scenario(
        self, _mock_write_runtime_config
    ):
        for scenario, expected in (
            (constants.DEVELOPER_SCENARIO, "reload"),
            (constants.SERVER_SCENARIO, None),
            (constants.CI_SCENARIO, None),
        ):
            with self.subTest(scenario=scenario):
                config = self._make_config(scenario)
                config.dev_mode = "reload"
                ComposeServiceBuilder(config).build()
                self.assertEqual(
                    self._dev_flag_from_command(config.compose_service.command),
                    expected,
                )

    @patch("dev_project.compose.service_builder.persist_runtime_config")
    def test_pre_commit_start_omits_dev_mode(self, _mock_write_runtime_config):
        config = self._make_config()
        config.dev_mode = "reload,qweb"
        config.arguments = replace(config.arguments, start_precommit=True)
        ComposeServiceBuilder(config).build()
        service = config.compose_service
        self.assertNotIn("--dev", service.command)
        self.assertIn(constants.RUN_PRE_COMMIT_ENTRYPOINT, service.command)


class DevModeComposeProbeTests(unittest.TestCase):
    SAMPLE_COMPOSE = """
services:
  db:
    image: postgres:16
  odoo:
    image: odoo:test
    command:
      - python3
      - -m
      - dev_project.inside_docker_app.run_odoo
      - --
      - /home/odoo/odoo/odoo-bin
      - -c
      - /home/odoo/odoo.conf
      - --dev
      - reload,qweb
"""

    def test_extract_odoo_compose_command(self):
        from tests.integration.dev_mode_probe import (
            dev_flag_from_compose_command,
            extract_odoo_compose_command,
        )

        command = extract_odoo_compose_command(self.SAMPLE_COMPOSE)
        self.assertEqual(
            dev_flag_from_compose_command(command),
            "reload,qweb",
        )

    def test_extract_odoo_compose_command_without_dev(self):
        from tests.integration.dev_mode_probe import (
            dev_flag_from_compose_command,
            extract_odoo_compose_command,
        )

        compose = self.SAMPLE_COMPOSE.replace("      - --dev\n      - reload,qweb\n", "")
        command = extract_odoo_compose_command(compose)
        self.assertIsNone(dev_flag_from_compose_command(command))
