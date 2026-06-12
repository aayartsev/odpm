"""Tests for debug profile plan preview and runtime step evaluation."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.plan.debug_profile_preview import (
    debug_profile_needs_update,
    normalized_debug_profile_text_from_disk,
    preview_debug_profile_text,
)
from dev_project.plan import OdpmPlan, PlanStep
from dev_project.plan.diff import PlanFileDiff, build_plan_diffs
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.prepare.runtime import evaluate_runtime_debug_profile
from dev_project.project_env.debug_profile import write_debug_profile
from dev_project.scenario_policy import ScenarioPolicy

from tests.debug_profile_test_helpers import make_debugger_env_mock


class PlanDebugProfilePreviewTests(unittest.TestCase):
    def _developer_config(self, project_dir: str) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        return config

    def _project_env(self, project_dir: str) -> MagicMock:
        odoo_src = os.path.join(project_dir, "sources", "odoo")
        os.makedirs(odoo_src, exist_ok=True)
        from dev_project.project_env.types import MappedPath

        return make_debugger_env_mock(
            project_dir=project_dir,
            mapped_folders=[MappedPath(local=odoo_src, docker="/home/odoo/odoo")],
        )

    def test_preview_debug_profile_text_returns_schema_v1(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            env = self._project_env(project_dir)
            text = preview_debug_profile_text(env)
            self.assertIsNotNone(text)
            payload = json.loads(text or "{}")
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["debugger"]["port"], 5678)

    def test_debug_profile_needs_update_when_file_missing_without_project_env(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._developer_config(project_dir)
            needs_update, reason = debug_profile_needs_update(config, None)
            self.assertTrue(needs_update)
            self.assertIn("missing", reason)

    def test_debug_profile_needs_update_when_preview_differs_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._developer_config(project_dir)
            env = self._project_env(project_dir)
            needs_update, reason = debug_profile_needs_update(config, env)
            self.assertTrue(needs_update)
            self.assertIn("changed", reason)

    def test_debug_profile_noop_when_preview_matches_disk(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._developer_config(project_dir)
            env = self._project_env(project_dir)
            write_debug_profile(env)
            needs_update, reason = debug_profile_needs_update(config, env)
            self.assertFalse(needs_update)
            self.assertIn("unchanged", reason)
            on_disk = normalized_debug_profile_text_from_disk(project_dir)
            self.assertEqual(on_disk, preview_debug_profile_text(env))

    def test_evaluate_runtime_debug_profile_skipped_for_ci(self) -> None:
        config = MagicMock()
        config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        self.assertIsNone(evaluate_runtime_debug_profile(config, MagicMock()))

    def test_evaluate_runtime_debug_profile_run_for_developer(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._developer_config(project_dir)
            env = self._project_env(project_dir)
            step = evaluate_runtime_debug_profile(config, env)
            self.assertIsNotNone(step)
            assert step is not None
            self.assertEqual(step.id, "ide.debug_profile")
            self.assertEqual(step.outcome, "run")
            self.assertTrue(step.should_execute())

    def test_diff_debug_profile_returns_unified_diff_when_file_missing(self) -> None:
        from dev_project.plan.diff import diff_debug_profile

        with tempfile.TemporaryDirectory() as project_dir:
            config = self._developer_config(project_dir)
            env = self._project_env(project_dir)
            diff = diff_debug_profile(config, env)
            self.assertIsNotNone(diff)
            assert diff is not None
            self.assertEqual(diff.path, constants.ODPM_DEBUG_PROFILE_REL_PATH)
            self.assertIn("path_mappings", diff.unified_diff or "")

    def test_build_plan_diffs_includes_debug_profile(self) -> None:
        plan = OdpmPlan(
            steps=(
                PlanStep(
                    "ide.debug_profile",
                    "Write debug profile",
                    "run",
                    False,
                    "debug profile missing",
                ),
            )
        )
        config = MagicMock()
        config.project_dir = "/tmp/project"
        project_env = MagicMock()
        with unittest.mock.patch(
            "dev_project.plan.diff.diff_debug_profile",
            return_value=PlanFileDiff(
                path=constants.ODPM_DEBUG_PROFILE_REL_PATH,
                unified_diff="---\n+++",
                summary="+1 -0 lines",
            ),
        ):
            diffs = build_plan_diffs(
                plan,
                config,
                OdpmCliArgs(plan_show_diff=True),
                project_env,
            )
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].path, constants.ODPM_DEBUG_PROFILE_REL_PATH)


if __name__ == "__main__":
    unittest.main()
