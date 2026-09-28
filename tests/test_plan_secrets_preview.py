import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.plan import OdpmPlan, PlanStep
from dev_project.host.context import HostProjectContext
from dev_project.plan.diff import build_plan_diffs, diff_secrets_materialize_summary
from dev_project.plan.secrets_preview import secrets_needs_update
from dev_project.prepare import make_prepare_context
from dev_project.prepare.steps_secrets import evaluate_secrets_materialize
from dev_project.project_env.secrets import import_secrets_from_path, materialize_secrets
from dev_project.scenario_policy import ScenarioPolicy


class PlanSecretsPreviewTests(unittest.TestCase):
    def _write_external(self, directory: str, secrets: dict[str, str]) -> str:
        path = os.path.join(directory, "external.json")
        Path(path).write_text(
            json.dumps({"schema_version": 1, "secrets": secrets}),
            encoding="utf-8",
        )
        return path

    def test_secrets_needs_update_when_runtime_missing(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir, self._write_external(project_dir, {"a": "1"})
            )
            needs_update, reason = secrets_needs_update(project_dir)
            self.assertTrue(needs_update)
            self.assertIn("missing", reason)

    def test_secrets_noop_when_runtime_matches_source(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir, self._write_external(project_dir, {"a": "1"})
            )
            materialize_secrets(project_dir)
            needs_update, reason = secrets_needs_update(project_dir)
            self.assertFalse(needs_update)
            self.assertIn("up to date", reason)

    def test_diff_summary_shows_key_count_without_values(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir, self._write_external(project_dir, {"a": "1", "b": "2"})
            )
            diff = diff_secrets_materialize_summary(project_dir)
            self.assertIsNotNone(diff)
            assert diff is not None
            self.assertIn("2 secret keys", diff.summary or "")
            self.assertIsNone(diff.unified_diff)
            plan = OdpmPlan(
                steps=(
                    PlanStep(
                        "secrets.materialize",
                        "desc",
                        "update",
                        True,
                        "reason",
                    ),
                ),
                warnings=(),
            )
            host_ctx = HostProjectContext(
                project_dir=project_dir,
                program_dir="/opt/odpm",
                config_home_dir=project_dir,
                policy=ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO),
                user_env=MagicMock(),
                arguments=OdpmCliArgs(plan_show_diff=True),
                user_settings=MagicMock(),
                project_settings=MagicMock(),
                docker_layout=MagicMock(),
                addon_layout=MagicMock(),
            )
            diffs = build_plan_diffs(plan, host_ctx, OdpmCliArgs(plan_show_diff=True), None)
            self.assertEqual(len(diffs), 1)
            self.assertIn("2 secret keys", diffs[0].summary or "")

    def test_fetch_diff_shows_key_count_without_values(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir,
                self._write_external(project_dir, {"token": "sk_live_must_not_leak"}),
            )
            plan = OdpmPlan(
                steps=(
                    PlanStep(
                        "secrets.fetch",
                        "Fetch secrets via provider fake",
                        "update",
                        True,
                        "remote provider configured",
                    ),
                ),
                warnings=(),
            )
            host_ctx = HostProjectContext(
                project_dir=project_dir,
                program_dir="/opt/odpm",
                config_home_dir=project_dir,
                policy=ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO),
                user_env=MagicMock(),
                arguments=OdpmCliArgs(plan_show_diff=True),
                user_settings=MagicMock(),
                project_settings=MagicMock(),
                docker_layout=MagicMock(),
                addon_layout=MagicMock(),
            )
            diffs = build_plan_diffs(
                plan, host_ctx, OdpmCliArgs(plan_show_diff=True), None
            )
            self.assertEqual(len(diffs), 1)
            summary = diffs[0].summary or ""
            self.assertIn("secret keys", summary)
            self.assertNotIn("sk_live_must_not_leak", summary)
            self.assertIsNone(diffs[0].unified_diff)

    def test_plan_step_skips_for_ci(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            ctx = make_prepare_context(
                config, MagicMock(), MagicMock(), OdpmCliArgs()
            )
            step = evaluate_secrets_materialize(ctx)
            self.assertEqual(step.id, "secrets.materialize")
            self.assertEqual(step.outcome, "skip")


if __name__ == "__main__":
    unittest.main()
