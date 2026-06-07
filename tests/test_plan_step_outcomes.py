"""Tests for plan step outcome evaluation helpers."""

import tempfile
import unittest
from dev_project.host_cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.plan import PlanStep
from dev_project.plan_compose_preview import (
    compose_service_needs_update,
    preview_compose_service,
    vscode_settings_up_to_date,
)
from dev_project.prepare.steps_docker import evaluate_docker_engine_check
from dev_project.prepare.steps_project import evaluate_update_links
from dev_project.prepare_registry import (
    _evaluate_compose_generate,
    _evaluate_compose_service,
    make_prepare_context,
)
from dev_project.scenario_policy import ScenarioPolicy


class PlanComposePreviewTests(unittest.TestCase):
    def _config(self, project_dir: str) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.arguments = OdpmCliArgs()
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.compute_venv_lock_hash.return_value = "hash"
        config.python_version = "3.12"
        return config

    def _developer_compose_config(self) -> MagicMock:
        config = MagicMock()
        config.project_dir = "/tmp/odpm-test-project"
        config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.container_run_mode = constants.RUN_MODE_ODOO
        config.arguments = OdpmCliArgs()
        config.dev_mode = False
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.docker_project_dir = "/home/odoo"
        config.docker_inside_app = "/home/odoo/dev_project/inside_docker_app"
        config.docker_venv_dir = "/home/odoo/.venv"
        config.platform_name = "odoo"
        config.odoo_version = "19.0"
        config.init_modules = ""
        config.update_modules = ""
        config.docker_odoo_project_dir_path = "/home/odoo/extra-addons/project"
        config.docker_temp_tests_dir = "/home/odoo/odoo_tests"
        config.requirements_txt = []
        config.config_to_json.return_value = b"{}"
        config.generate_odoo_conf_docker_data = MagicMock()
        return config

    @patch("dev_project.compose_service_builder.write_runtime_config")
    def test_preview_compose_service_does_not_write_runtime_config(self, mock_write):
        preview_compose_service(self._developer_compose_config())
        mock_write.assert_not_called()

    @patch(
        "dev_project.plan_compose_preview.preview_runtime_config_text",
        return_value='{\n  "arguments": {"branch": "dev"},\n  "schema_version": 1\n}\n',
    )
    @patch(
        "dev_project.plan_compose_preview.normalized_runtime_config_text_from_disk",
        return_value='{\n  "arguments": {"branch": "dev"},\n  "schema_version": 1\n}\n',
    )
    def test_compose_service_noop_when_normalized_runtime_matches(
        self, _mock_disk, _mock_preview
    ):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = tmp + "/" + constants.ODPM_RUNTIME_DIR_REL_PATH
            Path(runtime_dir).mkdir(parents=True)
            Path(runtime_dir, "config.json").write_text(
                '{"arguments": {"plan": true, "branch": "dev"}, '
                '"schema_version": 1, "venv_lock_hash": "hash"}',
                encoding="utf-8",
            )
            ctx = make_prepare_context(
                self._config(tmp),
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(),
            )
            needs_update, reason = compose_service_needs_update(ctx)
            self.assertFalse(needs_update)
            self.assertIn("unchanged", reason)

    def test_compose_service_noop_when_runtime_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = tmp + "/" + constants.ODPM_RUNTIME_DIR_REL_PATH
            import os
            from pathlib import Path

            Path(runtime_dir).mkdir(parents=True)
            Path(runtime_dir, "config.json").write_text(
                '{"venv_lock_hash": "hash"}',
                encoding="utf-8",
            )
            ctx = make_prepare_context(
                self._config(tmp),
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(),
            )
            needs_update, reason = compose_service_needs_update(ctx)
            self.assertFalse(needs_update)
            self.assertIn("unchanged", reason)

    def test_vscode_settings_noop_when_files_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path

            vscode_dir = Path(tmp) / ".vscode"
            vscode_dir.mkdir()
            (vscode_dir / "settings.json").write_text('{"python": "3.12"}', encoding="utf-8")
            (vscode_dir / "launch.json").write_text("{}", encoding="utf-8")
            config = self._config(tmp)
            self.assertTrue(vscode_settings_up_to_date(config))


class ComposeGenerateOutcomeTests(unittest.TestCase):
    @patch(
        "dev_project.prepare_registry.compose_generate_needs_execute",
        return_value=(False, "docker-compose.yml matches preview"),
    )
    def test_compose_generate_noop_when_preview_matches(self, _mock_generate):
        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.project_dir = tmp
            ctx = make_prepare_context(
                config,
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(),
            )
            step = _evaluate_compose_generate(ctx)
            self.assertEqual(step.outcome, "noop")
            self.assertEqual(step.reason, "docker-compose.yml matches preview")


class ComposeServiceGenerateAlignmentTests(unittest.TestCase):
    def test_compose_service_runs_when_generate_needs_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            from tests.plan_smoke_helpers import seed_migrated_project_layout

            seed_migrated_project_layout(Path(tmp), include_root_compose=False)
            config = MagicMock()
            config.project_dir = tmp
            config.arguments = OdpmCliArgs()
            config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            config.compute_venv_lock_hash.return_value = "hash"
            ctx = make_prepare_context(config, MagicMock(), MagicMock(), OdpmCliArgs())
            service = _evaluate_compose_service(ctx)
            generate = _evaluate_compose_generate(ctx)
            self.assertEqual(service.outcome, "run")
            self.assertEqual(generate.outcome, "update")
            self.assertTrue(service.should_execute())
            self.assertTrue(generate.should_execute())


class EvaluateDockerEngineCheckTests(unittest.TestCase):
    def test_skips_when_check_system_disabled(self) -> None:
        ctx = MagicMock()
        ctx.config.check_system = False

        step = evaluate_docker_engine_check(ctx)

        self.assertEqual(step.outcome, "skip")
        self.assertFalse(step.required)
        self.assertFalse(step.should_execute())
        self.assertIn("skipped", step.reason)

    def test_runs_when_check_system_enabled(self) -> None:
        ctx = MagicMock()
        ctx.config.check_system = True

        step = evaluate_docker_engine_check(ctx)

        self.assertEqual(step.outcome, "run")
        self.assertTrue(step.required)
        self.assertTrue(step.should_execute())


class EvaluateUpdateLinksTests(unittest.TestCase):
    def test_runs_when_create_module_links_disabled(self) -> None:
        ctx = MagicMock()
        ctx.config.create_module_links = False

        step = evaluate_update_links(ctx)

        self.assertEqual(step.outcome, "run")
        self.assertTrue(step.should_execute())


class PlanStepTests(unittest.TestCase):
    def test_should_execute_for_run_and_update_only(self):
        self.assertTrue(
            PlanStep("id", "desc", "run", True, "reason").should_execute()
        )
        self.assertTrue(
            PlanStep("id", "desc", "update", True, "reason").should_execute()
        )
        self.assertFalse(
            PlanStep("id", "desc", "noop", True, "reason").should_execute()
        )
        self.assertFalse(
            PlanStep("id", "desc", "skip", False, "reason").should_execute()
        )


if __name__ == "__main__":
    unittest.main()
