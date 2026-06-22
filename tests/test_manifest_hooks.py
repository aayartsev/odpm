"""Tests for manifest lifecycle hooks and hook runner registry."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.errors import ConfigError, PipelineError
from dev_project.extensions.context import ExtensionHostContext
from dev_project.extensions.hooks import parse_hook_phase, run_lifecycle_hooks
from dev_project.extensions.registry import (
    get_hook_runner,
    load_hook_runners,
    register_hook_runner,
    reset_extension_registry_state,
)
from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_SPEC
from dev_project.compose.fragments import render_compose_services_block
from dev_project.prepare.execute import execute_prepare
from dev_project.runtime_coordinator import RuntimeCoordinator
from dev_project.host.cli.args import OdpmCliArgs
from tests.fixtures.compose.mailpit_fragment import MAILPIT_COMPOSE_FRAGMENT


class _RecordingHookRunner:
    name = "test.hooks.recorder"

    def __init__(self) -> None:
        self.phases: list[str] = []

    def run_post_prepare(self, ctx: ExtensionHostContext) -> None:
        self.phases.append("post_prepare")

    def run_pre_up(self, ctx: ExtensionHostContext) -> None:
        self.phases.append("pre_up")


class ParseHookPhaseTests(unittest.TestCase):
    def test_parses_shell_and_plugin_entries(self):
        shell, plugins = parse_hook_phase(
            {
                "post_prepare": [
                    ["echo", "hi"],
                    "my.plugin",
                ]
            },
            "post_prepare",
        )
        self.assertEqual(shell, (("echo", "hi"),))
        self.assertEqual(plugins, ("my.plugin",))

    def test_rejects_invalid_entry(self):
        with self.assertRaises(ConfigError):
            parse_hook_phase({"pre_up": [123]}, "pre_up")


class RunLifecycleHooksTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    @patch("dev_project.extensions.hooks.run_or_raise")
    def test_runs_shell_hooks_in_order(self, mock_run):
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_hooks={"pre_up": [["echo", "one"], ["echo", "two"]]},
        )
        run_lifecycle_hooks(ext, "pre_up", cwd="/tmp/project")
        self.assertEqual(
            [call.args[0] for call in mock_run.call_args_list],
            [("echo", "one"), ("echo", "two")],
        )
        mock_run.assert_any_call(("echo", "one"), cwd="/tmp/project")
        mock_run.assert_any_call(("echo", "two"), cwd="/tmp/project")

    @patch("dev_project.extensions.hooks.run_or_raise")
    def test_shell_hook_failure_raises_pipeline_error(self, mock_run):
        mock_run.side_effect = Exception("boom")
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_hooks={"post_prepare": [["false"]]},
        )
        with self.assertRaises(PipelineError):
            run_lifecycle_hooks(ext, "post_prepare", cwd="/tmp/project")

    def test_runs_registered_plugin_runner(self):
        runner = _RecordingHookRunner()
        register_hook_runner(runner.name, runner)
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_hooks={"post_prepare": [runner.name]},
        )
        run_lifecycle_hooks(ext, "post_prepare", cwd="/tmp/project")
        self.assertEqual(runner.phases, ["post_prepare"])

    def test_unknown_plugin_id_raises_config_error(self):
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_hooks={"pre_up": ["missing.plugin"]},
        )
        with self.assertRaises(ConfigError):
            run_lifecycle_hooks(ext, "pre_up", cwd="/tmp/project")


class HookRunnerRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    def test_register_hook_runner(self):
        runner = _RecordingHookRunner()
        register_hook_runner(runner.name, runner)
        self.assertIs(get_hook_runner(runner.name), runner)
        load_hook_runners()


class MailpitReferenceTests(unittest.TestCase):
    def test_mailpit_spec_renders_golden_fragment(self):
        block = render_compose_services_block({"mailpit": dict(MAILPIT_SERVICE_SPEC)})
        self.assertEqual(block, MAILPIT_COMPOSE_FRAGMENT)


class ExecutePrepareHooksIntegrationTests(unittest.TestCase):
    @patch("dev_project.prepare.execute.get_prepare_steps", return_value=())
    @patch("dev_project.extensions.hooks.run_lifecycle_hooks")
    def test_execute_prepare_runs_post_prepare_hooks(
        self, mock_run_hooks, _mock_steps
    ):
        ctx = MagicMock()
        ctx.host_ctx = MagicMock()
        ctx.host_ctx.project_dir = "/tmp/project"
        ctx.host_ctx.update_lock = False
        ctx.host_ctx.skip_git_update = False
        ctx.host_ctx.sync_manifest_locks = False
        ctx.extension_host.return_value = MagicMock()
        execute_prepare(ctx)
        mock_run_hooks.assert_called_once_with(
            ctx.extension_host.return_value,
            "post_prepare",
            cwd="/tmp/project",
        )


class RuntimeCoordinatorHooksIntegrationTests(unittest.TestCase):
    @patch(
        "dev_project.runtime_coordinator.should_force_recreate_compose_for_host",
        return_value=False,
    )
    @patch("dev_project.runtime_coordinator.run_logged", return_value=0)
    @patch("dev_project.extensions.hooks.run_lifecycle_hooks")
    @patch("dev_project.database.resolve.ensure_no_blocking_database_drift")
    @patch("dev_project.database.adopt.adopt_database_baseline")
    def test_pre_up_runs_before_compose_up(
        self,
        _mock_adopt,
        _mock_drift,
        mock_run_hooks,
        mock_run_logged,
        _mock_force_recreate,
    ):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.program_dir = "/opt/odpm"
        config.config_home_dir = "/tmp/project"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.user_env = MagicMock()
        config.user_env.odoo_port = 8069
        config.user_settings = MagicMock()
        config.project_settings = MagicMock()
        config.docker_layout = MagicMock()
        config.addon_layout = MagicMock()
        config.arguments = OdpmCliArgs(skip_start=False)
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        coordinator = RuntimeCoordinator(OdpmCliArgs(skip_start=False), config, MagicMock())
        coordinator.handle_build_image = MagicMock(return_value=False)
        coordinator.write_debug_profile = MagicMock()
        coordinator.configure_ide = MagicMock()
        call_order: list[str] = []

        def record_hooks(*_args, **_kwargs):
            call_order.append("pre_up")

        def record_up(*_args, **_kwargs):
            call_order.append("compose_up")
            return 0

        mock_run_hooks.side_effect = record_hooks
        mock_run_logged.side_effect = record_up
        coordinator.run_after_prepare()
        self.assertEqual(call_order, ["pre_up", "compose_up"])
        mock_run_hooks.assert_called_once()
        self.assertEqual(mock_run_hooks.call_args.args[1], "pre_up")


if __name__ == "__main__":
    unittest.main()
