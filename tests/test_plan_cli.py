"""Tests for odpm plan subcommand and plan CLI helpers."""

import io
import json
import sys
import tempfile
import unittest
from dev_project.host_cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
import dev_project.host_cli.parse_args as parse_args_module
from dev_project.host_cli import params
from dev_project.host_cli.parse_args import parse_cli_args
from dev_project.plan_cli import is_plan_mode
from dev_project.scenario_policy import ScenarioPolicy
from tests.plan_smoke_helpers import seed_migrated_project_layout


class PlanCliHelperTests(unittest.TestCase):
    def test_is_plan_mode_true_when_plan_flag_set(self):
        self.assertTrue(is_plan_mode(OdpmCliArgs(plan=True)))

    def test_is_plan_mode_true_when_plan_subcommand_selected(self):
        self.assertTrue(is_plan_mode(OdpmCliArgs(command="plan")))

    def test_is_plan_mode_false_otherwise(self):
        self.assertFalse(is_plan_mode(OdpmCliArgs()))


class PlanSubcommandParseTests(unittest.TestCase):
    def test_parse_args_plan_subcommand_sets_plan_flag(self):
        args = parse_args_module.parse_args(["plan"])
        self.assertTrue(args.plan)

    def test_parse_args_plan_subcommand_with_project_flags(self):
        args = parse_args_module.parse_args(["plan", "--skip-start", "--no-git-update"])
        self.assertTrue(args.plan)
        self.assertTrue(args.skip_start)
        self.assertTrue(args.no_git_update)

    def test_parse_args_plan_subcommand_with_plan_flags(self):
        args = parse_args_module.parse_args(
            ["plan", "--plan-format", "json", "--plan-strict"]
        )
        self.assertTrue(args.plan)
        self.assertEqual(args.plan_format, "json")
        self.assertTrue(args.plan_strict)

    def test_parse_args_deprecated_plan_flag_unchanged(self):
        args = parse_args_module.parse_args(["--plan", "--plan-no-docker"])
        self.assertTrue(args.plan)
        self.assertTrue(args.plan_no_docker)

    def test_parse_args_plan_subcommand_sets_command_dest(self):
        args = parse_args_module.parse_args(["plan", "--skip-start"])
        self.assertEqual(args.command, params.PLAN_SUBCOMMAND)

    def test_plan_subcommand_help_shows_plan_description(self):
        stdout = io.StringIO()
        with patch.object(sys, "stdout", stdout):
            with self.assertRaises(SystemExit) as ctx:
                parse_args_module.parse_args(["plan", "-h"])
        self.assertEqual(ctx.exception.code, 0)
        help_text = stdout.getvalue()
        self.assertIn("plan", help_text)
        self.assertIn("prepare", help_text.lower())


class PlanSubcommandPipelineTests(unittest.TestCase):
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
        config.arguments = OdpmCliArgs()
        config.check_system = True
        config.create_module_links = True
        config.dockerfile_template_name = "debian_12_dockerfile"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        config.docker_compose_command = "docker compose"
        return config

    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_plan_subcommand_prints_json_to_stdout(self, _mock_setup):
        from dev_project.odpm_pipeline import OdpmPipeline

        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp))
            pipeline = OdpmPipeline(
                parse_cli_args(["plan", "--plan-format", "json"]),
                "/opt/odpm",
            )
            pipeline.config = self._config(tmp)
            pipeline.project_environment = MagicMock()
            with patch("builtins.print") as mock_print:
                pipeline.run()
            mock_print.assert_called_once()
            payload = json.loads(mock_print.call_args[0][0])
            self.assertEqual(payload["plan_version"], 1)

    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    @patch("dev_project.plan_format.plan_has_required_changes", return_value=False)
    def test_plan_subcommand_equivalent_to_plan_flag(
        self, _mock_required, _mock_setup
    ):
        from dev_project.odpm_pipeline import OdpmPipeline

        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp))
            config = self._config(tmp)
            env = MagicMock()
            with patch("dev_project.plan.OdpmPlanner") as mock_planner:
                mock_planner.build.return_value = MagicMock(steps=(), warnings=(), diffs=())
                pipeline_sub = OdpmPipeline(
                    parse_cli_args(["plan", "--skip-start"]),
                    "/opt/odpm",
                )
                pipeline_sub.config = config
                pipeline_sub.project_environment = env
                pipeline_sub.run()

                pipeline_flag = OdpmPipeline(
                    parse_cli_args(["--plan", "--skip-start"]),
                    "/opt/odpm",
                )
                pipeline_flag.config = config
                pipeline_flag.project_environment = env
                pipeline_flag.run()

            self.assertEqual(mock_planner.build.call_count, 2)
            for call in mock_planner.build.call_args_list:
                self.assertEqual(call[0][1].plan, True)


if __name__ == "__main__":
    unittest.main()
