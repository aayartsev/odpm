"""Tests for odpm --plan JSON output and --plan-strict."""

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.inside_docker_app import parse_args as parse_args_module
from dev_project.plan import OdpmPlan, PlanStep, format_plan
from dev_project.plan_format import (
    PLAN_JSON_VERSION,
    format_plan_json,
    format_plan_table,
    plan_has_required_changes,
    plan_to_dict,
)
from dev_project.scenario_policy import ScenarioPolicy
from tests.plan_smoke_helpers import seed_migrated_project_layout


class PlanFormatHelperTests(unittest.TestCase):
    def test_plan_has_required_changes_when_required_run_exists(self):
        plan = OdpmPlan(
            steps=(
                PlanStep("git.materialize", "desc", "run", True, "reason"),
                PlanStep("vscode.settings", "desc", "noop", False, "reason"),
            )
        )
        self.assertTrue(plan_has_required_changes(plan))

    def test_plan_has_required_changes_false_for_optional_run(self):
        plan = OdpmPlan(
            steps=(PlanStep("docker.engine.check", "desc", "run", False, "reason"),)
        )
        self.assertFalse(plan_has_required_changes(plan))

    def test_plan_has_required_changes_false_for_required_noop(self):
        plan = OdpmPlan(
            steps=(PlanStep("compose.service", "desc", "noop", True, "reason"),)
        )
        self.assertFalse(plan_has_required_changes(plan))


class PlanJsonFormatTests(unittest.TestCase):
    def _plan(self) -> OdpmPlan:
        from dev_project.plan_diff import PlanFileDiff

        return OdpmPlan(
            steps=(
                PlanStep(
                    "compose.up",
                    "Run docker compose up",
                    "run",
                    True,
                    "start compose stack without --force-recreate (stack healthy)",
                ),
            ),
            warnings=("example warning",),
            diffs=(
                PlanFileDiff(
                    path=".odpm/runtime/config.json",
                    unified_diff="---\n+++",
                    summary="+1 -1 lines",
                ),
            ),
        )

    def _config(self) -> MagicMock:
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        return config

    @patch(
        "dev_project.plan_format.compose_up_force_recreate_value",
        return_value=False,
    )
    def test_plan_to_dict_includes_version_steps_warnings_compose_up_and_diffs(
        self, _mock_force
    ):
        payload = plan_to_dict(self._plan(), self._config(), Namespace())
        self.assertEqual(payload["plan_version"], PLAN_JSON_VERSION)
        self.assertEqual(payload["steps"][0]["outcome"], "run")
        self.assertEqual(payload["steps"][0]["id"], "compose.up")
        self.assertNotIn("action", payload["steps"][0])
        self.assertEqual(payload["warnings"], ["example warning"])
        self.assertEqual(payload["compose_up"], {"force_recreate": False})
        self.assertEqual(len(payload["diffs"]), 1)

    @patch(
        "dev_project.plan_format.compose_up_force_recreate_value",
        return_value=None,
    )
    def test_plan_to_dict_omits_compose_up_when_step_missing(self, _mock_force):
        plan = OdpmPlan(steps=())
        payload = plan_to_dict(plan, self._config(), Namespace(plan_no_docker=True))
        self.assertNotIn("compose_up", payload)

    @patch(
        "dev_project.plan_format.compose_up_force_recreate_value",
        return_value=False,
    )
    def test_format_plan_json_is_valid_json(self, _mock_force):
        text = format_plan_json(self._plan(), self._config(), Namespace())
        payload = json.loads(text)
        self.assertEqual(payload["plan_version"], PLAN_JSON_VERSION)

    def test_format_plan_defaults_to_table(self):
        plan = OdpmPlan(
            steps=(
                PlanStep("git.materialize", "Clone", "run", True, "clone repos"),
            )
        )
        text = format_plan(plan)
        self.assertIn("Action   Required  ID", text)
        self.assertIn("git.materialize", text)

    @patch(
        "dev_project.plan_format.compose_up_force_recreate_value",
        return_value=True,
    )
    def test_format_plan_json_mode(self, _mock_force):
        plan = self._plan()
        config = self._config()
        text = format_plan(plan, Namespace(plan_format="json"), config)
        payload = json.loads(text)
        self.assertEqual(payload["compose_up"]["force_recreate"], True)


class PlanStrictPipelineTests(unittest.TestCase):
    def setUp(self):
        self._recreate_patcher = patch(
            "dev_project.plan_compose_runtime.should_force_recreate_compose",
            return_value=False,
        )
        self._recreate_patcher.start()

    def tearDown(self):
        self._recreate_patcher.stop()

    def _config(self, project_dir: str) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.arguments = Namespace()
        config.check_system = True
        config.create_module_links = True
        config.dockerfile_template_name = "debian_12_dockerfile"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        config.docker_compose_command = "docker compose"
        return config

    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_plan_strict_exits_one_when_required_changes_exist(self, _mock_setup):
        from dev_project.odpm_pipeline import OdpmPipeline

        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp))
            pipeline = OdpmPipeline(
                Namespace(plan=True, plan_strict=True, skip_start=True),
                "/opt/odpm",
            )
            pipeline.config = self._config(tmp)
            pipeline.project_environment = MagicMock()
            with self.assertRaises(SystemExit) as ctx:
                pipeline.run()
            self.assertEqual(ctx.exception.code, 1)

    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    @patch("dev_project.plan_format.plan_has_required_changes", return_value=False)
    def test_plan_strict_exits_zero_when_no_required_changes(
        self, _mock_required, _mock_setup
    ):
        from dev_project.odpm_pipeline import OdpmPipeline

        pipeline = OdpmPipeline(Namespace(plan=True, plan_strict=True), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        with patch("sys.exit") as mock_exit:
            pipeline.run()
        mock_exit.assert_not_called()

    def test_parse_args_accepts_plan_format_and_strict(self):
        args = parse_args_module.parse_args(
            ["--plan", "--plan-format", "json", "--plan-strict"]
        )
        self.assertTrue(args.plan)
        self.assertEqual(args.plan_format, "json")
        self.assertTrue(args.plan_strict)


if __name__ == "__main__":
    unittest.main()
