"""Unit tests for odpm --plan detectors and pipeline integration."""

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.plan import (
    OdpmPlanner,
    deps_lock_file_exists,
    format_plan,
    project_template_needs_upgrade,
    runtime_config_stale,
    skip_git_update,
)
from dev_project.project_materializer import ProjectMaterializer
from dev_project.scenario_policy import ScenarioPolicy


class PlanPredicateTests(unittest.TestCase):
    def test_skip_git_update_reads_no_git_update_flag(self):
        self.assertFalse(skip_git_update(Namespace(no_git_update=False)))
        self.assertTrue(skip_git_update(Namespace(no_git_update=True)))

    def test_project_template_needs_upgrade_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(
                project_template_needs_upgrade(
                    tmp,
                    constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
                    constants.COMPOSE_TEMPLATE_MARKERS,
                )
            )

    def test_runtime_config_stale_when_file_missing(self):
        config = MagicMock()
        config.project_dir = "/tmp/missing-runtime"
        self.assertTrue(runtime_config_stale(config))

    def test_runtime_config_stale_when_hash_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp) / constants.ODPM_RUNTIME_DIR_REL_PATH
            runtime_dir.mkdir(parents=True)
            config_path = runtime_dir / "config.json"
            config_path.write_text('{"venv_lock_hash": "old"}', encoding="utf-8")
            config = MagicMock()
            config.project_dir = tmp
            config.compute_venv_lock_hash.return_value = "new"
            self.assertTrue(runtime_config_stale(config))

    def test_runtime_config_stale_when_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp) / constants.ODPM_RUNTIME_DIR_REL_PATH
            runtime_dir.mkdir(parents=True)
            config_path = runtime_dir / "config.json"
            config_path.write_text('{"venv_lock_hash": "same"}', encoding="utf-8")
            config = MagicMock()
            config.project_dir = tmp
            config.compute_venv_lock_hash.return_value = "same"
            self.assertFalse(runtime_config_stale(config))


class OdpmPlannerTests(unittest.TestCase):
    def _config(self, *, project_dir: str, args: Namespace | None = None) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.arguments = args or Namespace()
        config.check_system = True
        config.create_module_links = True
        config.dockerfile_template_name = "debian_12_dockerfile"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        return config

    def test_plan_materialize_git_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(config, Namespace())
            step_ids = [step.id for step in plan.steps]
            self.assertIn("git.materialize", step_ids)
            self.assertNotIn("git.ensure_present", step_ids)
            self.assertIn("compose.up", step_ids)

    def test_plan_ensure_git_when_no_git_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(
                project_dir=tmp,
                args=Namespace(no_git_update=True),
            )
            plan = OdpmPlanner.build(config, Namespace(no_git_update=True))
            step_ids = [step.id for step in plan.steps]
            self.assertIn("git.ensure_present", step_ids)
            self.assertNotIn("git.materialize", step_ids)
            self.assertNotIn("git.checkout", step_ids)

    def test_plan_update_lock_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(config, Namespace(update_lock=True))
            step_ids = [step.id for step in plan.steps]
            self.assertIn("git.update_lock", step_ids)
            self.assertNotIn("compose.up", step_ids)

    def test_plan_warns_on_update_lock_with_no_git_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(
                config,
                Namespace(update_lock=True, no_git_update=True),
            )
            self.assertTrue(
                any("cannot be used together" in warning for warning in plan.warnings)
            )

    def test_plan_includes_lock_apply_when_lock_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / constants.DEPS_LOCK_REL_PATH
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text('{"schema_version": 1}', encoding="utf-8")
            self.assertTrue(deps_lock_file_exists(tmp))
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(config, Namespace())
            self.assertIn("git.lock_apply", [step.id for step in plan.steps])

    def test_format_plan_renders_table(self):
        from dev_project.plan import OdpmPlan, PlanStep

        text = format_plan(
            OdpmPlan(
                steps=(
                    PlanStep("git.materialize", "Clone git repos", True),
                    PlanStep("vscode.settings", "Update VS Code", False),
                ),
                warnings=("example warning",),
            )
        )
        self.assertIn("git.materialize", text)
        self.assertIn("yes", text)
        self.assertIn("no", text)
        self.assertIn("example warning", text)


class ProjectMaterializerDryRunTests(unittest.TestCase):
    def test_dry_run_delegates_to_planner(self):
        config = MagicMock()
        args = Namespace()
        with patch("dev_project.plan.OdpmPlanner") as mock_planner:
            mock_planner.build.return_value = MagicMock()
            result = ProjectMaterializer().run(
                config,
                MagicMock(),
                MagicMock(),
                args,
                dry_run=True,
            )
        mock_planner.build.assert_called_once_with(config, args)
        self.assertIs(result, mock_planner.build.return_value)


class OdpmPipelinePlanTests(unittest.TestCase):
    @patch("dev_project.plan.format_plan", return_value="plan-table")
    @patch("dev_project.plan.OdpmPlanner")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_plan_skips_prepare_and_logs_table(
        self,
        mock_setup,
        mock_prepare,
        mock_planner,
        mock_format_plan,
    ):
        from dev_project.odpm_pipeline import OdpmPipeline

        pipeline = OdpmPipeline(Namespace(plan=True), "/opt/odpm")
        pipeline.config = MagicMock()
        mock_planner.build.return_value = MagicMock()

        pipeline.run()

        mock_prepare.assert_not_called()
        mock_planner.build.assert_called_once_with(pipeline.config, pipeline.args)
        mock_format_plan.assert_called_once()


if __name__ == "__main__":
    unittest.main()
