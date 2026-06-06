"""Tests for odpm --plan --plan-show-diff file diffs."""

import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
import dev_project.host_cli.parse_args as parse_args_module
from dev_project.plan import OdpmPlan, OdpmPlanner, PlanStep, format_plan
from dev_project.plan_diff import (
    PlanFileDiff,
    build_plan_diffs,
    diff_dockerignore,
    diff_line_summary,
    diff_runtime_config,
)
from dev_project.scenario_policy import ScenarioPolicy
from tests.plan_smoke_helpers import seed_migrated_project_layout


class PlanDiffHelperTests(unittest.TestCase):
    def test_diff_line_summary_counts_changed_lines(self):
        unified = (
            "--- a/file\n"
            "+++ b/file\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        self.assertEqual(diff_line_summary(unified), "+1 -1 lines")


class PlanRuntimeConfigDiffTests(unittest.TestCase):
    @patch(
        "dev_project.plan_diff.preview_runtime_config_text",
        return_value='{\n  "preview": true\n}\n',
    )
    @patch(
        "dev_project.plan_diff.normalized_runtime_config_text_from_disk",
        return_value='{\n  "on_disk": true\n}\n',
    )
    def test_diff_runtime_config_when_payload_differs(self, _mock_disk, _mock_preview):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        diff = diff_runtime_config(config)
        self.assertIsNotNone(diff)
        assert diff is not None
        self.assertEqual(diff.path, constants.ODPM_RUNTIME_CONFIG_REL_PATH)
        self.assertIn('"on_disk": true', diff.unified_diff or "")
        self.assertIn('"preview": true', diff.unified_diff or "")

    @patch(
        "dev_project.plan_diff.preview_runtime_config_text",
        return_value='{\n  "same": true\n}\n',
    )
    @patch(
        "dev_project.plan_diff.normalized_runtime_config_text_from_disk",
        return_value='{\n  "same": true\n}\n',
    )
    def test_diff_runtime_config_none_when_unchanged(self, _mock_disk, _mock_preview):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        self.assertIsNone(diff_runtime_config(config))


class PlanDockerignoreDiffTests(unittest.TestCase):
    def test_diff_dockerignore_when_root_differs_from_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp), include_root_compose=False)
            config = MagicMock()
            config.project_dir = tmp
            config.project_dockerignore_template_path = os.path.join(
                tmp,
                constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
            )
            Path(tmp, constants.DOCKERIGNORE).write_text(
                "stale-root-content\n",
                encoding="utf-8",
            )
            diff = diff_dockerignore(config)
            self.assertIsNotNone(diff)
            assert diff is not None
            self.assertEqual(diff.path, constants.DOCKERIGNORE)
            self.assertIn("stale-root-content", diff.unified_diff or "")


class BuildPlanDiffsTests(unittest.TestCase):
    def _plan_with_step(self, step_id: str, outcome: str) -> OdpmPlan:
        return OdpmPlan(
            steps=(
                PlanStep(
                    step_id,
                    "description",
                    outcome,  # type: ignore[arg-type]
                    True,
                    "reason",
                ),
            )
        )

    def test_build_plan_diffs_empty_without_flag(self):
        plan = self._plan_with_step("compose.service", "update")
        config = MagicMock()
        self.assertEqual(build_plan_diffs(plan, config, Namespace()), ())

    @patch(
        "dev_project.plan_diff.diff_runtime_config",
        return_value=PlanFileDiff(
            path=constants.ODPM_RUNTIME_CONFIG_REL_PATH,
            unified_diff="---\n+++",
            summary="+1 -1 lines",
        ),
    )
    def test_build_plan_diffs_includes_runtime_config(self, _mock_diff):
        plan = self._plan_with_step("compose.service", "update")
        config = MagicMock()
        diffs = build_plan_diffs(
            plan,
            config,
            Namespace(plan_show_diff=True),
        )
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].path, constants.ODPM_RUNTIME_CONFIG_REL_PATH)

    def test_build_plan_diffs_deps_lock_summary_on_update_lock(self):
        plan = self._plan_with_step("git.lock_collect", "update")
        config = MagicMock()
        diffs = build_plan_diffs(
            plan,
            config,
            Namespace(plan_show_diff=True),
        )
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].path, constants.DEPS_LOCK_REL_PATH)
        self.assertEqual(diffs[0].summary, "will rewrite from resolved commits")
        self.assertIsNone(diffs[0].unified_diff)

    def test_build_plan_diffs_skips_noop_steps(self):
        plan = self._plan_with_step("compose.service", "noop")
        config = MagicMock()
        self.assertEqual(
            build_plan_diffs(plan, config, Namespace(plan_show_diff=True)),
            (),
        )

    @patch(
        "dev_project.plan_diff.diff_docker_compose",
        return_value=PlanFileDiff(
            path="docker-compose.yml",
            unified_diff="---\n+++",
            summary="+2 -1 lines",
        ),
    )
    def test_build_plan_diffs_includes_compose_generate(self, _mock_diff):
        plan = self._plan_with_step("compose.generate", "update")
        config = MagicMock()
        diffs = build_plan_diffs(
            plan,
            config,
            Namespace(plan_show_diff=True),
            MagicMock(),
        )
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].path, "docker-compose.yml")


class PlanDiffFormatTests(unittest.TestCase):
    def test_format_plan_renders_planned_changes(self):
        text = format_plan(
            OdpmPlan(
                steps=(),
                diffs=(
                    PlanFileDiff(
                        path=".odpm/runtime/config.json",
                        unified_diff="--- a/.odpm/runtime/config.json\n+++ b/.odpm/runtime/config.json\n@@\n-old\n+new\n",
                        summary="+1 -1 lines",
                    ),
                    PlanFileDiff(
                        path=constants.DEPS_LOCK_REL_PATH,
                        summary="will rewrite from resolved commits",
                    ),
                ),
            )
        )
        self.assertIn("Planned changes:", text)
        self.assertIn(".odpm/runtime/config.json (+1 -1 lines)", text)
        self.assertIn("-old", text)
        self.assertIn("+new", text)
        self.assertIn(
            f"{constants.DEPS_LOCK_REL_PATH}: will rewrite from resolved commits",
            text,
        )


class PlanDiffIntegrationTests(unittest.TestCase):
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
        config.project_dockerignore_template_path = os.path.join(
            project_dir,
            constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        return config

    @patch(
        "dev_project.plan_diff.diff_runtime_config",
        return_value=PlanFileDiff(
            path=constants.ODPM_RUNTIME_CONFIG_REL_PATH,
            unified_diff="---\n+++",
            summary="+1 -1 lines",
        ),
    )
    def test_planner_attaches_diffs_when_show_diff_enabled(self, mock_diff):
        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp), venv_lock_hash="stale")
            config = self._config(tmp)
            plan = OdpmPlanner.build(
                config,
                Namespace(plan_show_diff=True, skip_start=True),
            )
            self.assertTrue(plan.diffs)
            self.assertEqual(plan.diffs[0].path, constants.ODPM_RUNTIME_CONFIG_REL_PATH)
            mock_diff.assert_called_once_with(config)

    def test_parse_args_accepts_plan_show_diff(self):
        args = parse_args_module.parse_args(["--plan", "--plan-show-diff"])
        self.assertTrue(args.plan)
        self.assertTrue(args.plan_show_diff)


if __name__ == "__main__":
    unittest.main()
