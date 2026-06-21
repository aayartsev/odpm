"""Unit tests for odpm --plan detectors and pipeline integration."""

import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.plan import (
    OdpmPlanner,
    PlanStep,
    deps_lock_file_exists,
    format_plan,
    project_template_needs_upgrade,
    runtime_config_stale,
    skip_git_update,
)
from dev_project.prepare import (
    collect_execute_step_ids,
    evaluate_prepare_plan,
    make_prepare_context,
)
from dev_project.project_materializer import ProjectMaterializer
from dev_project.scenario_policy import ScenarioPolicy

from tests.debug_profile_test_helpers import make_debugger_env_mock


class PlanPredicateTests(unittest.TestCase):
    def test_skip_git_update_reads_no_git_update_flag(self):
        self.assertFalse(skip_git_update(OdpmCliArgs(no_git_update=False)))
        self.assertTrue(skip_git_update(OdpmCliArgs(no_git_update=True)))

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
    def setUp(self):
        self._recreate_patcher = patch(
            "dev_project.compose.runtime.should_force_recreate_compose",
            return_value=False,
        )
        self._recreate_patcher.start()

    def tearDown(self):
        self._recreate_patcher.stop()

    def _config(self, *, project_dir: str, args: OdpmCliArgs | None = None) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.arguments = args or OdpmCliArgs()
        config.user_settings = MagicMock()
        config.user_settings.check_system = True
        config.create_module_links = True
        config.dockerfile_template_name = "debian_12_dockerfile"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        config.docker_compose_command = "docker compose"
        return config

    def _step(self, plan, step_id: str) -> PlanStep:
        return next(step for step in plan.steps if step.id == step_id)

    def test_plan_includes_debug_profile_for_developer_with_project_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            project_env = make_debugger_env_mock(project_dir=tmp, mapped_folders=[])
            plan = OdpmPlanner.build(
                config,
                OdpmCliArgs(skip_start=True),
                project_env,
            )
            step = self._step(plan, "ide.debug_profile")
            self.assertEqual(step.outcome, "run")
            self.assertIn("changed", step.reason)

    def test_plan_omits_debug_profile_for_ci(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            project_env = make_debugger_env_mock(project_dir=tmp, mapped_folders=[])
            plan = OdpmPlanner.build(
                config,
                OdpmCliArgs(skip_start=True),
                project_env,
            )
            self.assertFalse(any(step.id == "ide.debug_profile" for step in plan.steps))

    def test_plan_materialize_git_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(config, OdpmCliArgs())
            materialize = self._step(plan, "git.materialize")
            ensure = self._step(plan, "git.ensure_present")
            self.assertEqual(materialize.outcome, "run")
            self.assertEqual(ensure.outcome, "skip")
            self.assertEqual(self._step(plan, "compose.up").outcome, "run")
            self.assertIn(
                "without --force-recreate",
                self._step(plan, "compose.up").reason,
            )

    def test_plan_ensure_git_when_no_git_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(
                project_dir=tmp,
                args=OdpmCliArgs(no_git_update=True),
            )
            plan = OdpmPlanner.build(config, OdpmCliArgs(no_git_update=True))
            self.assertEqual(self._step(plan, "git.ensure_present").outcome, "run")
            self.assertEqual(self._step(plan, "git.materialize").outcome, "skip")
            self.assertEqual(self._step(plan, "git.checkout").outcome, "skip")

    def test_plan_update_lock_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(config, OdpmCliArgs(update_lock=True))
            self.assertEqual(self._step(plan, "git.materialize").outcome, "run")
            self.assertEqual(self._step(plan, "git.lock_collect").outcome, "update")
            self.assertFalse(any(step.id == "compose.up" for step in plan.steps))

    def test_plan_warns_on_update_lock_with_no_git_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(
                config,
                OdpmCliArgs(update_lock=True, no_git_update=True),
            )
            self.assertTrue(
                any("cannot be used together" in warning for warning in plan.warnings)
            )

    def test_plan_lock_apply_is_run_when_lock_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / constants.DEPS_LOCK_REL_PATH
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text('{"schema_version": 1}', encoding="utf-8")
            self.assertTrue(deps_lock_file_exists(tmp))
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(config, OdpmCliArgs())
            self.assertEqual(self._step(plan, "git.lock_apply").outcome, "run")

    def test_plan_shows_compose_noop_when_runtime_fresh_and_compose_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            from tests.plan_smoke_helpers import seed_migrated_project_layout

            seed_migrated_project_layout(Path(tmp))
            config = self._config(project_dir=tmp)
            plan = OdpmPlanner.build(config, OdpmCliArgs())
            self.assertEqual(self._step(plan, "template.dockerfile").outcome, "update")
            self.assertEqual(self._step(plan, "compose.service").outcome, "noop")
            self.assertEqual(self._step(plan, "compose.generate").outcome, "noop")

    def test_format_plan_renders_table(self):
        from dev_project.plan import OdpmPlan

        text = format_plan(
            OdpmPlan(
                steps=(
                    PlanStep(
                        "git.materialize",
                        "Clone git repos",
                        "run",
                        True,
                        "clone or update git repos",
                    ),
                    PlanStep(
                        "vscode.settings",
                        "Update VS Code",
                        "noop",
                        False,
                        "VS Code settings already present",
                    ),
                ),
                warnings=("example warning",),
            )
        )
        self.assertIn("Action   Required  ID", text)
        self.assertIn("RUN", text)
        self.assertIn("NOOP", text)
        self.assertIn("git.materialize", text)
        self.assertIn("example warning", text)


class PrepareRegistryContractTests(unittest.TestCase):
    def _config(self, *, project_dir: str) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.arguments = OdpmCliArgs()
        config.user_settings = MagicMock()
        config.user_settings.check_system = True
        config.create_module_links = True
        config.dockerfile_template_name = "debian_12_dockerfile"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        return config

    def _ctx(self, args: OdpmCliArgs, project_dir: str):
        return make_prepare_context(
            self._config(project_dir=project_dir),
            MagicMock(),
            MagicMock(),
            args,
        )

    def test_execute_ids_are_run_or_update_subset_of_plan(self):
        scenarios = (
            OdpmCliArgs(),
            OdpmCliArgs(no_git_update=True),
            OdpmCliArgs(update_lock=True),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for args in scenarios:
                ctx = self._ctx(args, tmp)
                plan_steps = evaluate_prepare_plan(ctx)
                execute_ids = list(collect_execute_step_ids(ctx))
                plan_by_id = {step.id: step for step in plan_steps}
                self.assertEqual(len(plan_steps), len(PREPARE_STEP_IDS))
                for step_id in execute_ids:
                    self.assertIn(step_id, plan_by_id)
                    self.assertTrue(plan_by_id[step_id].should_execute())
                self.assertEqual(
                    execute_ids,
                    [step.id for step in plan_steps if step.should_execute()],
                )

    def test_lock_apply_follows_map_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / constants.DEPS_LOCK_REL_PATH
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text('{"schema_version": 1}', encoding="utf-8")
            ctx = self._ctx(OdpmCliArgs(), tmp)
            step_ids = [step.id for step in evaluate_prepare_plan(ctx)]
            self.assertEqual(self._step_outcome(ctx, "git.lock_apply"), "run")
            self.assertLess(
                step_ids.index("project.map_folders"),
                step_ids.index("git.lock_apply"),
            )

    def test_stale_runtime_config_marks_compose_service_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx(OdpmCliArgs(), tmp)
            self.assertEqual(self._step_outcome(ctx, "compose.service"), "update")
            self.assertNotIn("venv.runtime_config", collect_execute_step_ids(ctx))

    def test_fresh_runtime_config_marks_compose_service_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            from tests.plan_smoke_helpers import seed_migrated_project_layout

            seed_migrated_project_layout(Path(tmp))
            ctx = self._ctx(OdpmCliArgs(), tmp)
            self.assertEqual(self._step_outcome(ctx, "compose.service"), "noop")
            self.assertEqual(self._step_outcome(ctx, "compose.generate"), "noop")

    def test_developer_plan_releases_ports_when_check_system_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            config.user_settings.check_system = False
            ctx = make_prepare_context(
                config,
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(),
            )
            self.assertEqual(self._step_outcome(ctx, "docker.engine.check"), "skip")
            self.assertEqual(self._step_outcome(ctx, "docker.ports.release"), "run")
            self.assertIn("docker.ports.release", collect_execute_step_ids(ctx))

    def test_server_plan_skips_port_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(project_dir=tmp)
            config.policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
            ctx = make_prepare_context(
                config,
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(),
            )
            self.assertEqual(self._step_outcome(ctx, "docker.ports.release"), "skip")
            self.assertNotIn("docker.ports.release", collect_execute_step_ids(ctx))

    def _step_outcome(self, ctx, step_id: str) -> str:
        return next(
            step.outcome for step in evaluate_prepare_plan(ctx) if step.id == step_id
        )


PREPARE_STEP_IDS = [
    "git.lock_load",
    "git.ensure_present",
    "git.materialize",
    "project.map_folders",
    "git.lock_apply",
    "template.dockerfile",
    "template.dockerignore",
    "docker.engine.check",
    "docker.ports.release",
    "template.odoo_conf",
    "database.drift",
    "compose.template",
    "compose.fragments",
    "secrets.materialize",
    "compose.service",
    "compose.generate",
    "compose.validate",
    "git.checkout",
    "git.lock_collect",
    "git.lock_verify",
    "project.update_links",
]


class ProjectMaterializerDryRunTests(unittest.TestCase):
    def test_dry_run_delegates_to_build_plan(self):
        config = MagicMock()
        args = OdpmCliArgs()
        with patch("dev_project.project_materializer.build_plan") as mock_build_plan:
            mock_build_plan.return_value = MagicMock()
            result = ProjectMaterializer().run(
                config,
                MagicMock(),
                MagicMock(),
                args,
                dry_run=True,
            )
        mock_build_plan.assert_called_once_with(config, args)
        self.assertIs(result, mock_build_plan.return_value)


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

        pipeline = OdpmPipeline(OdpmCliArgs(plan=True), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        mock_planner.build.return_value = MagicMock()

        pipeline.run()

        mock_prepare.assert_not_called()
        mock_planner.build.assert_called_once_with(
            pipeline.config,
            pipeline.cli_args,
            pipeline.project_environment,
        )
        mock_format_plan.assert_called_once_with(
            mock_planner.build.return_value,
            pipeline.cli_args,
            pipeline.config,
        )


if __name__ == "__main__":
    unittest.main()
