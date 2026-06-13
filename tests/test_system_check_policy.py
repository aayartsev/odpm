"""Tests for SystemCheckPolicy gating matrix."""

import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.prepare.steps_compose import evaluate_compose_validate
from dev_project.prepare.steps_docker import (
    evaluate_docker_engine_check,
    evaluate_docker_ports_release,
)
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.system_check_policy import SystemCheckPolicy


class SystemCheckPolicyMatrixTests(unittest.TestCase):
    def _config(self, *, check_system: bool, scenario: str) -> MagicMock:
        config = MagicMock()
        config.check_system = check_system
        config.policy = ScenarioPolicy.from_scenario(scenario)
        return config

    def test_from_config_developer_check_system_enabled(self):
        policy = SystemCheckPolicy.from_config(
            self._config(check_system=True, scenario=constants.DEVELOPER_SCENARIO)
        )
        self.assertTrue(policy.beginner_git)
        self.assertTrue(policy.beginner_docker)
        self.assertTrue(policy.developer_port_release)
        self.assertTrue(policy.compose_validate)
        self.assertTrue(policy.file_system_on_init)

    def test_from_config_developer_check_system_disabled(self):
        policy = SystemCheckPolicy.from_config(
            self._config(check_system=False, scenario=constants.DEVELOPER_SCENARIO)
        )
        self.assertFalse(policy.beginner_git)
        self.assertFalse(policy.beginner_docker)
        self.assertTrue(policy.developer_port_release)
        self.assertTrue(policy.compose_validate)
        self.assertTrue(policy.file_system_on_init)

    def test_from_config_server_scenario(self):
        policy = SystemCheckPolicy.from_config(
            self._config(check_system=True, scenario=constants.SERVER_SCENARIO)
        )
        self.assertTrue(policy.beginner_git)
        self.assertTrue(policy.beginner_docker)
        self.assertFalse(policy.developer_port_release)

    def test_prepare_step_matrix(self):
        cases = (
            (
                constants.DEVELOPER_SCENARIO,
                True,
                ("run", "run", "run"),
            ),
            (
                constants.DEVELOPER_SCENARIO,
                False,
                ("skip", "run", "run"),
            ),
            (
                constants.SERVER_SCENARIO,
                True,
                ("run", "skip", "run"),
            ),
            (
                constants.CI_SCENARIO,
                False,
                ("skip", "skip", "run"),
            ),
        )
        for scenario, check_system, expected in cases:
            with self.subTest(scenario=scenario, check_system=check_system):
                config = self._config(check_system=check_system, scenario=scenario)
                ctx = MagicMock()
                ctx.config = config
                docker = evaluate_docker_engine_check(ctx)
                ports = evaluate_docker_ports_release(ctx)
                compose = evaluate_compose_validate(ctx)
                self.assertEqual(
                    (docker.outcome, ports.outcome, compose.outcome),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
