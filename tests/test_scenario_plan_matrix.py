"""Scenario × documented dry-run plan matrix (no Docker daemon required)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.plan import OdpmPlan, OdpmPlanner, PlanStep, format_plan
from dev_project.plan.compose_runtime import PLAN_NO_DOCKER_WARNING
from dev_project.prepare import make_prepare_context
from dev_project.project_env.secrets import import_secrets_from_path
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.scenario_plan_matrix_helpers import (
    build_matrix_plan,
    invalid_v2_manifest_payload,
    plan_has_step,
    plan_step,
    prepare_step_outcome,
    run_matrix_manifest_cli,
    run_matrix_plan_cli,
    seed_matching_v2_locks,
    seed_v1_deps_lock,
    sync_idle_compose_state,
)

SCENARIOS = tuple(constants.ODPM_SCENARIO_VALUES)


class _MatrixProjectTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()
        self._previous_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self._home)
        self._provision_seq = 0

    def tearDown(self) -> None:
        if self._previous_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._previous_home
        self._tmp.cleanup()

    def _provision(
        self,
        *,
        scenario: str = constants.DEVELOPER_SCENARIO,
        manifest_v2_mailpit: bool = False,
        locks_drift: bool = False,
        check_system: bool = False,
        odpm_ide: str = "vscode",
        name: str | None = None,
    ) -> Path:
        if name is None:
            self._provision_seq += 1
            name = f"project-{self._provision_seq}"
        return provision_minimal_odpm_project(
            Path(self._tmp.name) / name,
            scenario=scenario,
            manifest_v2_mailpit=manifest_v2_mailpit,
            locks_drift=locks_drift,
            check_system=check_system,
            odpm_ide=odpm_ide,
        )

    def _run_plan_cli(self, project_dir: Path, *argv: str) -> tuple[int, str]:
        return run_matrix_plan_cli(project_dir, self._home, *argv)

    def _run_manifest_cli(self, project_dir: Path, *argv: str) -> tuple[int, str]:
        return run_matrix_manifest_cli(project_dir, self._home, *argv)


class PlanMatrixCoreTests(_MatrixProjectTestCase):
    """Registry rows A1–A4, A10, A14–A17 and B1–B5, C1–C7."""

    def test_a1_plan_cli_all_scenarios(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                project_dir = self._provision(scenario=scenario)
                exit_code, _output = self._run_plan_cli(
                    project_dir,
                    "--skip-start",
                    "--no-git-update",
                )
                self.assertEqual(exit_code, 0)

    def test_a2_skip_start_omits_compose_up(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                project_dir = self._provision(scenario=scenario)
                plan, _pipeline = build_matrix_plan(
                    project_dir,
                    OdpmCliArgs(
                        plan=True,
                        skip_start=True,
                        no_git_update=True,
                    ),
                )
                self.assertFalse(plan_has_step(plan, "compose.up"))

    def test_a3_no_git_update_git_steps(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        plan, _pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, no_git_update=True),
        )
        self.assertEqual(plan_step(plan, "git.ensure_present").outcome, "run")
        self.assertEqual(plan_step(plan, "git.materialize").outcome, "skip")

    def test_a4_update_lock_collect_without_compose_up(self) -> None:
        project_dir = self._provision(scenario=constants.CI_SCENARIO)
        plan, _pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, update_lock=True),
        )
        self.assertEqual(plan_step(plan, "git.lock_collect").outcome, "update")
        self.assertFalse(plan_has_step(plan, "compose.up"))

    def test_a10_database_drift_step_present(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                project_dir = self._provision(scenario=scenario)
                plan, _pipeline = build_matrix_plan(
                    project_dir,
                    OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
                )
                self.assertTrue(plan_has_step(plan, "database.drift"))

    def test_a10_database_drift_first_run_warning(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        plan, _pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertTrue(
            any("last_run" in warning for warning in plan.warnings),
            msg=f"expected first-run drift warning, got: {plan.warnings}",
        )

    def test_a14_secrets_materialize_by_scenario(self) -> None:
        secrets_path = Path(self._tmp.name) / "secrets.json"
        secrets_path.write_text(
            json.dumps({"schema_version": 1, "secrets": {"k": "v"}}),
            encoding="utf-8",
        )
        os.chmod(secrets_path, 0o600)
        for scenario, expected in (
            (constants.DEVELOPER_SCENARIO, "update"),
            (constants.SERVER_SCENARIO, "update"),
            (constants.CI_SCENARIO, "skip"),
        ):
            with self.subTest(scenario=scenario):
                project_dir = self._provision(scenario=scenario)
                import_secrets_from_path(str(project_dir), str(secrets_path))
                _plan, pipeline = build_matrix_plan(
                    project_dir,
                    OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
                )
                self.assertEqual(
                    prepare_step_outcome(
                        pipeline,
                        OdpmCliArgs(skip_start=True, no_git_update=True),
                        "secrets.materialize",
                    ),
                    expected,
                )

    def test_a15_compose_steps_noop_on_idle_compose(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        sync_idle_compose_state(project_dir)
        plan, _pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(
                plan=True,
                skip_start=True,
                no_git_update=True,
                plan_strict=True,
            ),
        )
        self.assertEqual(plan_step(plan, "compose.service").outcome, "noop")
        self.assertEqual(plan_step(plan, "compose.generate").outcome, "noop")

    def test_a16_compose_fragments_on_v2_mailpit(self) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            manifest_v2_mailpit=True,
        )
        plan, _pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertIn(
            plan_step(plan, "compose.fragments").outcome,
            ("run", "update"),
        )

    @patch("dev_project.config.payload.write_runtime_config")
    def test_a17_plan_evaluate_does_not_write_runtime(self, mock_write) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            manifest_v2_mailpit=True,
        )
        build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        mock_write.assert_not_called()

    def test_b1_debug_profile_developer_only(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                project_dir = self._provision(scenario=scenario)
                plan, _pipeline = build_matrix_plan(
                    project_dir,
                    OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
                )
                if scenario == constants.DEVELOPER_SCENARIO:
                    self.assertTrue(plan_has_step(plan, "ide.debug_profile"))
                else:
                    self.assertFalse(plan_has_step(plan, "ide.debug_profile"))

    def test_b2_vscode_settings_by_scenario(self) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            odpm_ide="vscode",
        )
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertTrue(plan_has_step(plan, "vscode.settings"))

        ci_dir = self._provision(scenario=constants.CI_SCENARIO, odpm_ide="vscode")
        ci_plan, _ = build_matrix_plan(
            ci_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertFalse(plan_has_step(ci_plan, "vscode.settings"))

    def test_b3_pycharm_settings_developer_only(self) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            odpm_ide="pycharm",
        )
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertTrue(plan_has_step(plan, "pycharm.settings"))

    def test_b4_ci_build_image_step(self) -> None:
        project_dir = self._provision(scenario=constants.CI_SCENARIO)
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, build_image=True, skip_start=True),
        )
        self.assertTrue(plan_has_step(plan, "ci.build_image"))

        dev_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        dev_plan, _ = build_matrix_plan(
            dev_dir,
            OdpmCliArgs(plan=True, build_image=True, skip_start=True),
        )
        self.assertFalse(plan_has_step(dev_plan, "ci.build_image"))

    def test_b5_port_release_by_scenario(self) -> None:
        dev_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            check_system=True,
        )
        _plan, dev_pipeline = build_matrix_plan(
            dev_dir,
            OdpmCliArgs(plan=True, no_git_update=True),
        )
        self.assertEqual(
            prepare_step_outcome(
                dev_pipeline,
                OdpmCliArgs(no_git_update=True),
                "docker.ports.release",
            ),
            "run",
        )

        server_dir = self._provision(
            scenario=constants.SERVER_SCENARIO,
            check_system=True,
        )
        _plan, server_pipeline = build_matrix_plan(
            server_dir,
            OdpmCliArgs(plan=True, no_git_update=True),
        )
        self.assertEqual(
            prepare_step_outcome(
                server_pipeline,
                OdpmCliArgs(no_git_update=True),
                "docker.ports.release",
            ),
            "skip",
        )


class PlanMatrixWarningsTests(_MatrixProjectTestCase):
    """Registry rows A11–A13."""

    def test_a11_v1_lock_source_warning(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertTrue(
            any("deps.lock.json" in warning for warning in plan.warnings)
        )

    def test_a11_v2_lock_source_warning(self) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            manifest_v2_mailpit=True,
        )
        platform_uri = (project_dir / "platform" / "odoo").as_uri()
        seed_matching_v2_locks(project_dir, platform_uri=platform_uri)
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertTrue(
            any(
                "locks.git" in warning and "odpm.json" in warning
                for warning in plan.warnings
            )
        )

    def test_a12_locks_drift_warning(self) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            manifest_v2_mailpit=True,
            locks_drift=True,
        )
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertTrue(
            any(
                "locks.git" in warning and "deps.lock.json" in warning
                for warning in plan.warnings
            )
        )

    def test_a13_secrets_gitignore_warning(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        odpm_dir = project_dir / constants.PROJECT_SERVICE_DIRECTORY
        odpm_dir.mkdir(parents=True, exist_ok=True)
        (odpm_dir / "secrets.json").write_text(
            json.dumps({"schema_version": 1, "secrets": {"k": "v"}}) + "\n",
            encoding="utf-8",
        )
        (odpm_dir / ".gitignore").write_text("# no secrets entry\n", encoding="utf-8")
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        self.assertTrue(
            any(
                "secrets.json" in warning and ".odpm/.gitignore" in warning
                for warning in plan.warnings
            )
        )

    def test_a13_update_lock_with_no_git_update_warning(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, update_lock=True, no_git_update=True),
        )
        self.assertTrue(
            any(
                "--update-lock cannot be used together with --no-git-update"
                in warning
                for warning in plan.warnings
            )
        )


class PlanMatrixFlagsTests(_MatrixProjectTestCase):
    """Registry rows A5–A9."""

    def test_a5_plan_format_json(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        exit_code, output = self._run_plan_cli(
            project_dir,
            "--skip-start",
            "--no-git-update",
            "--plan-format",
            "json",
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads(output)
        self.assertIn("plan_version", payload)
        self.assertIn("steps", payload)
        self.assertIn("warnings", payload)

    def test_a6_plan_format_table(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        plan, pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        text = format_plan(plan, OdpmCliArgs(plan=True), pipeline.project_environment.host_ctx)
        self.assertIn("Action   Required  ID", text)

    def test_a7_plan_show_diff(self) -> None:
        project_dir = self._provision(scenario=constants.CI_SCENARIO)
        plan, _pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(
                plan=True,
                skip_start=True,
                update_lock=True,
                plan_show_diff=True,
            ),
        )
        diff_paths = {diff.path for diff in plan.diffs}
        self.assertIn(constants.DEPS_LOCK_REL_PATH, diff_paths)
        deps_diff = next(
            diff for diff in plan.diffs if diff.path == constants.DEPS_LOCK_REL_PATH
        )
        self.assertEqual(deps_diff.summary, "will rewrite from resolved commits")
        self.assertIsNone(deps_diff.unified_diff)

    def test_a8_plan_strict_nonzero_on_update_lock(self) -> None:
        project_dir = self._provision(scenario=constants.CI_SCENARIO)
        exit_code, _output = self._run_plan_cli(
            project_dir,
            "--update-lock",
            "--plan-strict",
        )
        self.assertEqual(exit_code, 1)

    def test_a8_plan_strict_json_format_nonzero_on_update_lock(self) -> None:
        project_dir = self._provision(scenario=constants.CI_SCENARIO)
        exit_code, output = self._run_plan_cli(
            project_dir,
            "--update-lock",
            "--plan-strict",
            "--plan-format",
            "json",
        )
        self.assertEqual(exit_code, 1)
        payload = json.loads(output)
        self.assertIn("steps", payload)

    @patch.object(OdpmPlanner, "build")
    def test_a8_plan_strict_zero_when_no_required_changes(
        self,
        mock_build: MagicMock,
    ) -> None:
        project_dir = self._provision(scenario=constants.CI_SCENARIO)
        mock_build.return_value = OdpmPlan(
            steps=(
                PlanStep(
                    "database.drift",
                    "Check database drift",
                    "noop",
                    True,
                    "baseline not created yet",
                ),
            ),
            warnings=(),
        )
        exit_code, _output = self._run_plan_cli(
            project_dir,
            "--skip-start",
            "--no-git-update",
            "--plan-strict",
        )
        self.assertEqual(exit_code, 0)

    def test_a9_plan_no_docker_warning(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        plan, _ = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, plan_no_docker=True),
        )
        self.assertIn(PLAN_NO_DOCKER_WARNING, plan.warnings)


class PlanMatrixManifestCliTests(_MatrixProjectTestCase):
    """Registry rows D1–D5."""

    def test_d1_manifest_validate_v1(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        exit_code, _output = self._run_manifest_cli(project_dir, "validate")
        self.assertEqual(exit_code, 0)

    def test_d2_manifest_validate_v2_mailpit(self) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            manifest_v2_mailpit=True,
        )
        exit_code, _output = self._run_manifest_cli(project_dir, "validate")
        self.assertEqual(exit_code, 0)

    def test_d3_manifest_validate_rejects_invalid_v2(self) -> None:
        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            manifest_v2_mailpit=True,
        )
        developing = project_dir / "developing" / "odpm.json"
        base = json.loads(developing.read_text(encoding="utf-8"))
        developing.write_text(
            json.dumps(invalid_v2_manifest_payload(base=base), indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ConfigError):
            self._run_manifest_cli(project_dir, "validate")

    def test_d4_manifest_migrate_prints_diff(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        exit_code, output = self._run_manifest_cli(project_dir, "migrate")
        self.assertEqual(exit_code, 0)
        self.assertIn("manifest_schema", output)

    def test_d5_manifest_migrate_includes_locks_from_deps_lock(self) -> None:
        project_dir = self._provision(scenario=constants.DEVELOPER_SCENARIO)
        platform_uri = (project_dir / "platform" / "odoo").as_uri()
        seed_v1_deps_lock(project_dir, platform_uri=platform_uri, commit="d" * 40)
        exit_code, output = self._run_manifest_cli(project_dir, "migrate")
        self.assertEqual(exit_code, 0)
        self.assertIn("locks", output)


class PlanMatrixComposeMarkersTests(_MatrixProjectTestCase):
    """Registry rows C7 and A16 compose content markers."""

    def test_c7_compose_markers_by_scenario(self) -> None:
        from tests.test_compose_generator import ComposeGeneratorPolicyTests

        helper = ComposeGeneratorPolicyTests()
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                project_dir = self._provision(scenario=scenario)
                helper._copy_compose_template(str(project_dir))
                env = helper._make_env(str(project_dir), scenario)
                env._compose.generate_docker_compose_file()
                content = (project_dir / "docker-compose.yml").read_text(
                    encoding="utf-8"
                )
                if scenario == constants.DEVELOPER_SCENARIO:
                    self.assertIn("5678", content)
                elif scenario == constants.SERVER_SCENARIO:
                    self.assertIn("odoo-base:dev", content)
                    self.assertIn("127.0.0.1:15432:5432", content)
                    self.assertNotIn("5678:5678", content)
                    self.assertNotIn(constants.PYTHONWARNINGS_ENV, content)
                elif scenario == constants.CI_SCENARIO:
                    self.assertIn("odoo-ci", content)

    def test_a16_mailpit_fragment_materialized(self) -> None:
        from dev_project.prepare.steps_compose import exec_compose_fragments

        project_dir = self._provision(
            scenario=constants.DEVELOPER_SCENARIO,
            manifest_v2_mailpit=True,
        )
        _plan, pipeline = build_matrix_plan(
            project_dir,
            OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
        )
        ctx = make_prepare_context(
            pipeline.config,
            pipeline.project_environment,
            pipeline.system_checker,
            OdpmCliArgs(skip_start=True, no_git_update=True),
        )
        exec_compose_fragments(ctx)
        fragment = project_dir / constants.COMPOSE_FRAGMENTS_DIR_REL_PATH / "mailpit.yml"
        self.assertTrue(fragment.is_file())
        self.assertIn("mailpit", fragment.read_text(encoding="utf-8"))


class PlanMatrixCliInProcessTests(_MatrixProjectTestCase):
    """In-process CLI smoke for plan JSON across scenarios (A1, A5)."""

    def test_plan_json_all_scenarios(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                project_dir = self._provision(scenario=scenario)
                exit_code, output = self._run_plan_cli(
                    project_dir,
                    "--skip-start",
                    "--no-git-update",
                    "--plan-format",
                    "json",
                )
                self.assertEqual(exit_code, 0)
                payload = json.loads(output)
                step_ids = {step["id"] for step in payload["steps"]}
                self.assertNotIn("compose.up", step_ids)
                self.assertIn("database.drift", step_ids)


if __name__ == "__main__":
    unittest.main()
