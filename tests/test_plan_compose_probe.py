"""Tests for compose stack probe in odpm --plan."""

import tempfile
import unittest
from dev_project.host_cli.args import OdpmCliArgs
from unittest.mock import MagicMock, patch

from dev_project import constants
import dev_project.host_cli.parse_args as parse_args_module
from dev_project.plan import OdpmPlanner, format_plan
from dev_project.plan_compose_runtime import (
    PLAN_NO_DOCKER_WARNING,
    evaluate_compose_up_plan,
    plan_probes_compose_stack,
)
from dev_project.prepare_registry import build_runtime_plan_warnings
from dev_project.scenario_policy import ScenarioPolicy


class PlanComposeRuntimeTests(unittest.TestCase):
    def _config(self, project_dir: str = "/tmp/project") -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.docker_compose_command = "docker compose"
        return config

    def test_plan_probes_compose_stack_by_default(self):
        self.assertTrue(plan_probes_compose_stack(OdpmCliArgs()))
        self.assertFalse(plan_probes_compose_stack(OdpmCliArgs(plan_no_docker=True)))

    @patch(
        "dev_project.plan_compose_runtime.should_force_recreate_compose",
        return_value=False,
    )
    def test_compose_up_reason_without_force_recreate_when_healthy(self, _mock):
        reason, warnings = evaluate_compose_up_plan(self._config(), OdpmCliArgs())
        self.assertIn("without --force-recreate", reason)
        self.assertIn("healthy", reason)
        self.assertEqual(warnings, ())

    @patch(
        "dev_project.plan_compose_runtime.should_force_recreate_compose",
        return_value=True,
    )
    def test_compose_up_reason_with_force_recreate_when_unhealthy(self, _mock):
        reason, warnings = evaluate_compose_up_plan(self._config(), OdpmCliArgs())
        self.assertIn("with --force-recreate", reason)
        self.assertIn("unhealthy", reason)
        self.assertEqual(warnings, ())

    def test_plan_no_docker_skips_probe_and_warns(self):
        reason, warnings = evaluate_compose_up_plan(
            self._config(),
            OdpmCliArgs(plan_no_docker=True),
        )
        self.assertIn("unknown", reason)
        self.assertEqual(warnings, (PLAN_NO_DOCKER_WARNING,))

    @patch("dev_project.prepare_registry.compose_up_would_run", return_value=True)
    @patch(
        "dev_project.prepare_registry.evaluate_compose_up_plan",
        return_value=("start compose stack with --force-recreate", ()),
    )
    def test_runtime_warnings_empty_when_probe_runs(self, _mock_eval, _mock_would_run):
        config = MagicMock()
        host_ctx = MagicMock()
        warnings = build_runtime_plan_warnings(config, OdpmCliArgs(), host_ctx)
        self.assertEqual(warnings, ())

    @patch("dev_project.prepare_registry.compose_up_would_run", return_value=True)
    @patch(
        "dev_project.prepare_registry.evaluate_compose_up_plan",
        return_value=("unknown", (PLAN_NO_DOCKER_WARNING,)),
    )
    def test_runtime_warnings_include_plan_no_docker_message(
        self, _mock_eval, _mock_would_run
    ):
        config = MagicMock()
        host_ctx = MagicMock()
        warnings = build_runtime_plan_warnings(
            config,
            OdpmCliArgs(plan_no_docker=True),
            host_ctx,
        )
        self.assertIn(PLAN_NO_DOCKER_WARNING, warnings)


class PlanComposeProbeIntegrationTests(unittest.TestCase):
    def _config(self, project_dir: str) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.arguments = OdpmCliArgs()
        config.check_system = True
        config.create_module_links = True
        config.dockerfile_template_name = "debian_12_dockerfile"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        config.docker_compose_command = "docker compose"
        return config

    @patch(
        "dev_project.plan_compose_runtime.should_force_recreate_compose",
        return_value=True,
    )
    def test_plan_table_shows_force_recreate_reason(self, _mock):
        with tempfile.TemporaryDirectory() as tmp:
            plan = OdpmPlanner.build(self._config(tmp), OdpmCliArgs())
            compose_up = next(step for step in plan.steps if step.id == "compose.up")
            self.assertIn("--force-recreate", compose_up.reason)
            text = format_plan(plan)
            self.assertIn("compose.up", text)

    def test_parse_args_accepts_plan_no_docker(self):
        args = parse_args_module.parse_args(["--plan", "--plan-no-docker"])
        self.assertTrue(args.plan)
        self.assertTrue(args.plan_no_docker)


if __name__ == "__main__":
    unittest.main()
