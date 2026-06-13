"""Smoke-style tests for odpm --plan on a migrated project layout."""

import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.plan import OdpmPlanner, format_plan
from dev_project.prepare import (
    collect_execute_step_ids,
    evaluate_prepare_plan,
    make_prepare_context,
)
from dev_project.prepare.steps_compose import (
    evaluate_compose_generate,
    evaluate_compose_service,
)
from dev_project.scenario_policy import ScenarioPolicy
from tests.plan_smoke_helpers import seed_migrated_project_layout


class OdpmPlanSmokeTests(unittest.TestCase):
    def _config(self, project_dir: str) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.arguments = OdpmCliArgs()
        config.check_system = True
        config.create_module_links = True
        config.dockerfile_template_name = "debian_12_dockerfile"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        config.python_version = "3.12"
        return config

    def test_plan_table_on_migrated_project_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp))
            plan = OdpmPlanner.build(self._config(tmp), OdpmCliArgs(skip_start=True))
            text = format_plan(plan)
            self.assertIn("Action   Required  ID", text)
            self.assertIn("git.materialize", text)
            self.assertIn("compose.service", text)
            self.assertIn("compose.generate", text)
            outcomes = {step.id: step.outcome for step in plan.steps}
            self.assertIn(outcomes["git.ensure_present"], ("skip",))
            self.assertIn(outcomes["compose.validate"], ("run",))

    def test_idle_migrated_project_shows_compose_noops(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp))
            ctx = make_prepare_context(
                self._config(tmp),
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(skip_start=True),
            )
            service = next(
                step for step in evaluate_prepare_plan(ctx) if step.id == "compose.service"
            )
            generate = next(
                step for step in evaluate_prepare_plan(ctx) if step.id == "compose.generate"
            )
            self.assertEqual(service.outcome, "noop")
            self.assertEqual(generate.outcome, "noop")

    def test_missing_root_compose_aligns_service_and_generate(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_migrated_project_layout(Path(tmp), include_root_compose=False)
            ctx = make_prepare_context(
                self._config(tmp),
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(),
            )
            service = evaluate_compose_service(ctx)
            generate = evaluate_compose_generate(ctx)
            self.assertTrue(service.should_execute())
            self.assertTrue(generate.should_execute())
            self.assertIn("compose.generate", service.reason)
            execute_ids = collect_execute_step_ids(ctx)
            self.assertIn("compose.service", execute_ids)
            self.assertIn("compose.generate", execute_ids)


if __name__ == "__main__":
    unittest.main()
