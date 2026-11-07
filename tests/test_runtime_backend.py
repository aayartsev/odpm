"""Runtime engine (Compose) contract and launch registry."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dev_project.errors import PipelineError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.prepare.runtime import (
    evaluate_runtime_compose_up,
    evaluate_runtime_ensure_base,
)
from dev_project.runtime_backend import LAUNCH_STEPS, get_runtime_backend
from dev_project.runtime_backend.compose import ComposeRuntimeBackend
from dev_project.host.ports import BootstrapHandle
from dev_project.runtime_coordinator import RuntimeCoordinator


from dev_project.config.assembly import ports_from_assembled, host_context_from_assembled
class ComposeRuntimeBackendStubTests(unittest.TestCase):
    def _backend(self) -> ComposeRuntimeBackend:
        config = MagicMock()
        config.runtime.docker_compose_command = "docker compose"
        config.runtime.no_log_prefix = False
        config.project_dir = "/tmp/project"
        host_ctx = host_context_from_assembled(config)
        return get_runtime_backend(
            host_ctx=host_ctx,
            bootstrap=BootstrapHandle(_assembled=config),
            project_env=MagicMock(),
        )

    def test_factory_returns_compose(self) -> None:
        self.assertIsInstance(self._backend(), ComposeRuntimeBackend)

    def test_down_logs_exec_not_implemented(self) -> None:
        backend = self._backend()
        for method_name in ("down", "logs", "exec"):
            with self.subTest(method=method_name):
                with self.assertRaises(PipelineError) as ctx:
                    getattr(backend, method_name)()
                message = str(ctx.exception).lower()
                self.assertIn(method_name, message)
                self.assertTrue(
                    "not implemented" in message or "не реализован" in message,
                    msg=message,
                )


class LaunchPlanVisibilityTests(unittest.TestCase):
    def test_ensure_base_tracks_compose_up(self) -> None:
        runtime = MagicMock()
        runtime.args = OdpmCliArgs()
        runtime.host_ctx = MagicMock()
        with patch(
            "dev_project.prepare.runtime.compose_up_would_run", return_value=True
        ):
            with patch(
                "dev_project.prepare.runtime.evaluate_compose_up_plan",
                return_value=("up", ()),
            ):
                ensure = evaluate_runtime_ensure_base(runtime)
                compose = evaluate_runtime_compose_up(runtime)
        self.assertIsNotNone(ensure)
        self.assertIsNotNone(compose)
        assert ensure is not None and compose is not None
        self.assertEqual(ensure.id, "runtime.ensure_base")
        self.assertEqual(ensure.outcome, "run")
        self.assertEqual(compose.id, "compose.up")

    def test_ensure_base_absent_when_compose_skipped(self) -> None:
        runtime = MagicMock()
        runtime.args = OdpmCliArgs(skip_start=True)
        runtime.host_ctx = MagicMock()
        with patch(
            "dev_project.prepare.runtime.compose_up_would_run", return_value=False
        ):
            self.assertIsNone(evaluate_runtime_ensure_base(runtime))
            self.assertIsNone(evaluate_runtime_compose_up(runtime))

    def test_launch_registry_order(self) -> None:
        self.assertEqual(
            [step.id for step in LAUNCH_STEPS],
            ["runtime.ensure_base", "compose.up"],
        )


class LaunchExecuteTests(unittest.TestCase):
    def _config(self) -> MagicMock:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.runtime.docker_compose_command = "docker compose"
        config.runtime.no_log_prefix = False
        config.user_env.odoo_port = 8069
        return config

    @patch("dev_project.runtime_backend.compose.BaseImageService")
    @patch(
        "dev_project.runtime_backend.compose.should_force_recreate_compose_for_host",
        return_value=False,
    )
    @patch("dev_project.runtime_backend.compose.run_logged", return_value=0)
    def test_execute_launch_steps_calls_backend(
        self, mock_run, _mock_should, mock_base
    ) -> None:
        config = self._config()
        project_env = MagicMock()
        project_env.bootstrap = BootstrapHandle(_assembled=config)
        coordinator = RuntimeCoordinator(
            ports_from_assembled(config, project_env, OdpmCliArgs()).runtime
        )
        from dev_project.runtime_backend import execute_launch_steps

        execute_launch_steps(coordinator)
        mock_base.return_value.ensure_base_image.assert_called_once()
        mock_run.assert_called_once()

    @patch("dev_project.runtime_backend.compose.BaseImageService")
    @patch("dev_project.runtime_backend.compose.run_logged", return_value=0)
    def test_execute_launch_steps_respects_skip_start_gate(
        self, mock_run, mock_base
    ) -> None:
        from dev_project.runtime_backend import execute_launch_steps

        config = self._config()
        project_env = MagicMock()
        project_env.bootstrap = BootstrapHandle(_assembled=config)
        coordinator = RuntimeCoordinator(
            ports_from_assembled(
                config, project_env, OdpmCliArgs(skip_start=True)
            ).runtime
        )
        execute_launch_steps(coordinator)
        mock_base.return_value.ensure_base_image.assert_not_called()
        mock_run.assert_not_called()

    @patch("dev_project.runtime_backend.compose.BaseImageService")
    @patch(
        "dev_project.runtime_backend.compose.should_force_recreate_compose_for_host",
        return_value=False,
    )
    @patch("dev_project.runtime_backend.compose.run_logged", return_value=0)
    def test_start_containers_force_bypasses_skip_start(
        self, mock_run, _mock_should, mock_base
    ) -> None:
        config = self._config()
        project_env = MagicMock()
        project_env.bootstrap = BootstrapHandle(_assembled=config)
        coordinator = RuntimeCoordinator(
            ports_from_assembled(
                config, project_env, OdpmCliArgs(skip_start=True)
            ).runtime
        )
        coordinator.start_containers()
        mock_base.return_value.ensure_base_image.assert_called_once()
        mock_run.assert_called_once()

    @patch("dev_project.runtime_coordinator.execute_launch_steps")
    @patch("dev_project.runtime_coordinator.run_lifecycle_hooks")
    @patch("dev_project.runtime_coordinator.ensure_no_blocking_database_drift")
    @patch("dev_project.runtime_coordinator.adopt_database_baseline")
    def test_run_after_prepare_keyboard_interrupt(
        self, _mock_adopt, _mock_drift, _mock_hooks, mock_launch
    ) -> None:
        mock_launch.side_effect = KeyboardInterrupt()
        config = self._config()
        config.bootstrap.manifest_view = None
        project_env = MagicMock()
        project_env.bootstrap = BootstrapHandle(_assembled=config)
        coordinator = RuntimeCoordinator(
            ports_from_assembled(config, project_env, OdpmCliArgs()).runtime
        )
        coordinator.handle_build_image = MagicMock(return_value=False)
        coordinator.write_debug_profile = MagicMock()
        coordinator.configure_ide = MagicMock()
        with patch(
            "dev_project.runtime_coordinator.host_summaries.log_control_c"
        ) as mock_log:
            with patch("dev_project.runtime_coordinator.sys.exit") as mock_exit:
                coordinator.run_after_prepare()
        mock_log.assert_called_once()
        mock_exit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
