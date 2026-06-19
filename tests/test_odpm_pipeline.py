import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.errors import ConfigError, PipelineError
from dev_project.odpm_pipeline import OdpmPipeline
from dev_project.runtime_coordinator import RuntimeCoordinator
from dev_project.scenario_policy import ScenarioPolicy
from tests.prepare_test_helpers import stub_prepare_service_executions


class RuntimeCoordinatorPolicyTests(unittest.TestCase):
    def _coordinator(self, **args_overrides) -> RuntimeCoordinator:
        args = OdpmCliArgs(**{"build_image": False, "skip_start": False, **args_overrides})
        config = MagicMock()
        config.user_env.odpm_ide = "vscode"
        project_env = MagicMock()
        return RuntimeCoordinator(args, config, project_env)

    @patch("dev_project.project_env.services.CiImageBuildService")
    def test_handle_build_image_rejects_non_ci_policy(self, mock_ci_service):
        coordinator = self._coordinator(build_image=True)
        coordinator.config.policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        )
        with self.assertRaises(PipelineError) as ctx:
            coordinator.handle_build_image()
        self.assertEqual(ctx.exception.exit_code, 1)
        mock_ci_service.assert_not_called()

    @patch("dev_project.project_env.services.CiImageBuildService")
    def test_handle_build_image_runs_for_ci_policy(self, mock_ci_service):
        coordinator = self._coordinator(build_image=True)
        coordinator.config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        self.assertTrue(coordinator.handle_build_image())
        mock_ci_service.assert_called_once_with(coordinator.project_env)
        mock_ci_service.return_value.build_ci_image.assert_called_once()

    @patch("dev_project.runtime_coordinator.VscodeConfigurator")
    def test_configure_vscode_skipped_when_policy_says_so(self, mock_vscode_cls):
        coordinator = self._coordinator()
        coordinator.config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        coordinator.configure_vscode()
        mock_vscode_cls.assert_not_called()

    @patch("dev_project.runtime_coordinator.VscodeConfigurator")
    def test_configure_vscode_runs_for_developer_policy(self, mock_vscode_cls):
        coordinator = self._coordinator()
        coordinator.config.policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        )
        coordinator.configure_vscode()
        mock_vscode_cls.assert_called_once_with(coordinator.project_env)
        mock_vscode_cls.return_value.update_vscode_debugger_launcher.assert_called_once()
        mock_vscode_cls.return_value.generate_vscode_settings_json.assert_called_once()

    @patch("dev_project.project_env.debug_profile.write_debug_profile")
    def test_write_debug_profile_skipped_without_debugpy(self, mock_write):
        coordinator = self._coordinator()
        coordinator.config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        coordinator.write_debug_profile()
        mock_write.assert_not_called()

    @patch("dev_project.project_env.debug_profile.write_debug_profile")
    def test_write_debug_profile_runs_for_developer_policy(self, mock_write):
        coordinator = self._coordinator()
        coordinator.config.policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        )
        coordinator.write_debug_profile()
        mock_write.assert_called_once_with(coordinator.project_env)

    @patch("dev_project.runtime_coordinator.PycharmConfigurator")
    @patch("dev_project.runtime_coordinator.VscodeConfigurator")
    @patch("dev_project.project_env.debug_profile.write_debug_profile")
    def test_run_after_prepare_writes_debug_profile_before_vscode(
        self, mock_write, mock_vscode_cls, mock_pycharm_cls
    ):
        coordinator = self._coordinator(skip_start=True)
        coordinator.config.policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        )
        call_order: list[str] = []

        def record_write(*_args, **_kwargs):
            call_order.append("write")

        def record_vscode(*_args, **_kwargs):
            call_order.append("vscode")
            return MagicMock()

        mock_write.side_effect = record_write
        mock_vscode_cls.side_effect = record_vscode

        coordinator.run_after_prepare()

        mock_write.assert_called_once_with(coordinator.project_env)
        mock_vscode_cls.assert_called_once_with(coordinator.project_env)
        mock_pycharm_cls.assert_not_called()
        self.assertEqual(call_order, ["write", "vscode"])


class OdpmPipelinePolicyTests(unittest.TestCase):
    def _pipeline(self, **args_overrides) -> OdpmPipeline:
        args = OdpmCliArgs(**{"build_image": False, "skip_start": False, **args_overrides})
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        return pipeline

    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    def test_handle_build_image_delegates_to_runtime_coordinator(self, mock_runtime_cls):
        pipeline = self._pipeline(build_image=True)
        mock_runtime_cls.return_value.handle_build_image.return_value = True
        self.assertTrue(pipeline.handle_build_image())
        mock_runtime_cls.assert_called_once_with(
            pipeline.cli_args, pipeline.config, pipeline.project_environment
        )
        mock_runtime_cls.return_value.handle_build_image.assert_called_once()

    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    def test_configure_vscode_delegates_to_runtime_coordinator(self, mock_runtime_cls):
        pipeline = self._pipeline()
        pipeline.configure_vscode()
        mock_runtime_cls.return_value.configure_vscode.assert_called_once()

    def test_compose_service_builder_uses_same_policy_instance(self):
        config = MagicMock()
        policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        config.policy = policy
        config.project_dir = "/tmp/odpm-test-project"
        config.container_run_mode = constants.RUN_MODE_ODOO
        config.arguments = OdpmCliArgs(
            d=None,
            translate=None,
            start_precommit=False,
            export_po_files=None,
            i=False,
            u=False,
            test=False,
            screencasts=False,
            odoo_bin=[],
        )
        config.dev_mode = False
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.docker_project_dir = "/home/odoo"
        config.docker_venv_dir = "/home/odoo/.venv"
        config.platform_name = "odoo"
        config.odoo_version = "19.0"
        config.init_modules = ""
        config.update_modules = ""
        config.docker_odoo_project_dir_path = "/home/odoo/extra-addons/project"
        config.docker_temp_tests_dir = "/home/odoo/odoo_tests"
        config.config_to_json.return_value = b"{}"
        config.generate_odoo_conf_docker_data = MagicMock()

        from dev_project.compose.service_builder import ComposeServiceBuilder

        with patch("dev_project.config.payload.write_runtime_config"):
            builder = ComposeServiceBuilder(config)
            builder.build()
        self.assertIs(builder.policy, policy)


class RuntimeCoordinatorComposeTests(unittest.TestCase):
    def _coordinator(self, config: MagicMock) -> RuntimeCoordinator:
        return RuntimeCoordinator(OdpmCliArgs(), config, MagicMock())

    def test_build_compose_up_argv_force_recreate_explicit(self):
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        self.assertEqual(
            self._coordinator(config).build_compose_up_argv(force_recreate=True),
            [
                "docker",
                "compose",
                "up",
                "--abort-on-container-exit",
                "--force-recreate",
            ],
        )

    def test_build_compose_up_argv_skips_force_recreate_when_healthy(self):
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        self.assertEqual(
            self._coordinator(config).build_compose_up_argv(force_recreate=False),
            [
                "docker",
                "compose",
                "up",
                "--abort-on-container-exit",
            ],
        )

    def test_build_compose_up_argv_with_no_log_prefix(self):
        config = MagicMock()
        config.docker_compose_command = "docker-compose"
        config.no_log_prefix = True
        self.assertEqual(
            self._coordinator(config).build_compose_up_argv(force_recreate=True),
            [
                "docker-compose",
                "up",
                "--no-log-prefix",
                "--abort-on-container-exit",
                "--force-recreate",
            ],
        )

    @patch(
        "dev_project.runtime_coordinator.should_force_recreate_compose",
        return_value=True,
    )
    def test_build_compose_up_argv_auto_detects_force_recreate(self, _mock_should):
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        argv = self._coordinator(config).build_compose_up_argv()
        self.assertIn("--force-recreate", argv)

    @patch(
        "dev_project.runtime_coordinator.should_force_recreate_compose",
        return_value=False,
    )
    def test_start_containers_uses_subprocess(self, _mock_should):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        config.user_env.odoo_port = 8069
        with patch("dev_project.runtime_coordinator.run_logged", return_value=0) as mock_run:
            self._coordinator(config).start_containers()
        mock_run.assert_called_once_with(
            ["docker", "compose", "up", "--abort-on-container-exit"],
            cwd="/tmp/project",
        )

    @patch(
        "dev_project.runtime_coordinator.should_force_recreate_compose",
        return_value=False,
    )
    def test_start_containers_raises_pipeline_error_on_compose_failure(
        self, _mock_should
    ):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        config.user_env.odoo_port = 8069
        config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        with patch("dev_project.runtime_coordinator.run_logged", return_value=17):
            with patch(
                "dev_project.runtime_coordinator.host_summaries.log_compose_failed"
            ) as mock_log_failed:
                with self.assertRaises(PipelineError) as ctx:
                    self._coordinator(config).start_containers()
        self.assertEqual(ctx.exception.exit_code, 17)
        self.assertEqual(str(ctx.exception), "")
        mock_log_failed.assert_called_once_with(17)

    @patch(
        "dev_project.runtime_coordinator.should_force_recreate_compose",
        return_value=False,
    )
    def test_start_containers_skips_host_compose_summary_for_developer(
        self, _mock_should
    ):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        config.user_env.odoo_port = 8069
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        with patch("dev_project.runtime_coordinator.run_logged", return_value=1):
            with patch(
                "dev_project.runtime_coordinator.host_summaries.log_compose_failed"
            ) as mock_log_failed:
                with self.assertRaises(PipelineError) as ctx:
                    self._coordinator(config).start_containers()
        self.assertEqual(ctx.exception.exit_code, 1)
        self.assertEqual(str(ctx.exception), "")
        mock_log_failed.assert_not_called()


class OdpmPipelineComposeTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    def test_build_compose_up_argv_delegates_to_runtime_coordinator(self, mock_runtime_cls):
        config = MagicMock()
        pipeline = OdpmPipeline(OdpmCliArgs(), "/opt/odpm")
        pipeline.project_environment = MagicMock()
        mock_runtime_cls.return_value.build_compose_up_argv.return_value = ["docker", "compose", "up"]
        argv = pipeline.build_compose_up_argv(config, force_recreate=True)
        mock_runtime_cls.assert_called_once_with(
            pipeline.cli_args, config, pipeline.project_environment
        )
        mock_runtime_cls.return_value.build_compose_up_argv.assert_called_once_with(
            force_recreate=True
        )
        self.assertEqual(argv, ["docker", "compose", "up"])

    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    def test_start_containers_delegates_to_runtime_coordinator(self, mock_runtime_cls):
        pipeline = OdpmPipeline(OdpmCliArgs(), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        pipeline.start_containers()
        mock_runtime_cls.return_value.start_containers.assert_called_once()


class OdpmPipelineRunTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_skips_compose_when_skip_start(
        self,
        mock_setup,
        mock_prepare,
        mock_runtime_cls,
    ):
        args = OdpmCliArgs(build_image=False, skip_start=True)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()

        pipeline.run()

        mock_runtime_cls.return_value.run_after_prepare.assert_called_once()

    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_skips_compose_when_update_lock(
        self,
        mock_setup,
        mock_prepare,
        mock_runtime_cls,
    ):
        args = OdpmCliArgs(build_image=False, skip_start=False, update_lock=True)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()

        pipeline.run()

        mock_runtime_cls.return_value.run_after_prepare.assert_called_once()

    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_stops_after_build_image(
        self,
        mock_setup,
        mock_prepare,
        mock_runtime_cls,
    ):
        args = OdpmCliArgs(build_image=True, skip_start=False)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()

        pipeline.run()

        mock_runtime_cls.return_value.run_after_prepare.assert_called_once()

    @patch("dev_project.odpm_pipeline.os.chdir")
    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_does_not_chdir(
        self,
        mock_setup,
        mock_prepare,
        mock_runtime_cls,
        mock_chdir,
    ):
        args = OdpmCliArgs(build_image=False, skip_start=False, update_lock=False)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()

        pipeline.run()

        mock_chdir.assert_not_called()
        mock_runtime_cls.return_value.run_after_prepare.assert_called_once()

    @patch("dev_project.odpm_pipeline._logger")
    @patch("dev_project.odpm_pipeline.RuntimeCoordinator")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    @patch("dev_project.odpm_pipeline.sys.exit")
    def test_run_exits_on_pipeline_error(
        self, mock_exit, mock_setup, mock_prepare, mock_runtime_cls, mock_logger
    ):
        pipeline = OdpmPipeline(OdpmCliArgs(build_image=True), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        mock_runtime_cls.return_value.run_after_prepare.side_effect = PipelineError(
            "forbidden", exit_code=1
        )
        pipeline.run()
        mock_exit.assert_called_once_with(1)
        mock_logger.error.assert_called_once_with("%s", "forbidden")

    @patch("dev_project.odpm_pipeline._logger")
    @patch("dev_project.odpm_pipeline.sys.exit")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_does_not_log_empty_odpm_error_message(
        self, mock_setup, mock_exit, mock_logger
    ):
        mock_setup.side_effect = ConfigError("", exit_code=0)
        pipeline = OdpmPipeline(OdpmCliArgs(), "/opt/odpm")
        pipeline.run()
        mock_exit.assert_called_once_with(0)
        mock_logger.error.assert_not_called()


class OdpmPipelineSetupTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.SystemChecker")
    @patch("dev_project.odpm_pipeline.CreateProjectEnvironment")
    @patch("dev_project.odpm_pipeline.Config")
    @patch("dev_project.odpm_pipeline.CreateUserEnvironment")
    @patch("dev_project.odpm_pipeline.ProjectDirManager")
    def test_setup_wires_pipeline_dependencies(
        self,
        mock_pd_manager_cls,
        mock_user_env_cls,
        mock_config_cls,
        mock_project_env_cls,
        mock_checker_cls,
    ):
        mock_config = MagicMock()
        mock_config.policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        mock_config_cls.return_value = mock_config
        mock_project_env = MagicMock()
        mock_project_env_cls.return_value = mock_project_env
        mock_checker = MagicMock()
        mock_checker_cls.return_value = mock_checker
        pipeline_args = OdpmCliArgs(build_image=False, skip_start=False)
        mock_pd_manager_cls.return_value.arguments = pipeline_args

        pipeline = OdpmPipeline(pipeline_args, "/opt/odpm")
        pipeline.setup()

        self.assertIs(pipeline.config, mock_config)
        self.assertIs(pipeline.project_environment, mock_project_env)
        self.assertIs(pipeline.system_checker, mock_checker)
        mock_config_cls.assert_called_once()
        mock_project_env_cls.assert_called_once_with(mock_config)
        mock_checker_cls.assert_called_once_with(mock_config, mock_project_env)
        mock_project_env.attach_system_checker.assert_called_once_with(mock_checker)

    @patch("dev_project.odpm_pipeline.SystemChecker")
    @patch("dev_project.odpm_pipeline.CreateProjectEnvironment")
    @patch("dev_project.odpm_pipeline.Config")
    @patch("dev_project.odpm_pipeline.CreateUserEnvironment")
    @patch("dev_project.odpm_pipeline.ProjectDirManager")
    def test_setup_syncs_cli_args_with_pd_manager_arguments(
        self,
        mock_pd_manager_cls,
        _mock_user_env_cls,
        mock_config_cls,
        _mock_project_env_cls,
        _mock_checker_cls,
    ):
        normalized = OdpmCliArgs(odoo_git_link="https://example.com/odoo.git")
        mock_pd = MagicMock()
        mock_pd.arguments = normalized
        mock_pd_manager_cls.return_value = mock_pd

        pipeline = OdpmPipeline(OdpmCliArgs(), "/opt/odpm")
        pipeline.setup()

        self.assertIs(pipeline.cli_args, normalized)
        self.assertIs(mock_config_cls.call_args[0][1], normalized)


class OdpmPipelinePrepareTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.ProjectMaterializer")
    def test_prepare_delegates_to_project_materializer(self, mock_materializer_cls):
        pipeline = OdpmPipeline(OdpmCliArgs(skip_start=True), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        pipeline.system_checker = MagicMock()
        materializer = MagicMock()
        mock_materializer_cls.return_value = materializer

        pipeline.prepare_project_files()

        mock_materializer_cls.assert_called_once_with()
        materializer.run.assert_called_once_with(
            pipeline.config,
            pipeline.project_environment,
            pipeline.system_checker,
            pipeline.cli_args,
        )

    def _pipeline_with_mocks(self, **args_overrides) -> OdpmPipeline:
        args = OdpmCliArgs(build_image=False, skip_start=True, **args_overrides)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        pipeline.system_checker = MagicMock()
        return pipeline

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_prepare_calls_materialize_git_repos_by_default(self, _mock_builder):
        pipeline = self._pipeline_with_mocks()
        with stub_prepare_service_executions() as service_mocks:
            pipeline.prepare_project_files()
            checkout_dependencies = service_mocks[-1]
        pipeline.config._git_repos.materialize_git_repos.assert_called_once_with(
            skip_build_date=False
        )
        pipeline.config._git_repos.ensure_git_repos_present.assert_not_called()
        checkout_dependencies.assert_called_once()

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_prepare_skips_git_when_no_git_update(self, _mock_builder):
        pipeline = self._pipeline_with_mocks(no_git_update=True)
        with stub_prepare_service_executions() as service_mocks:
            pipeline.prepare_project_files()
            checkout_dependencies = service_mocks[-1]
        pipeline.config._git_repos.ensure_git_repos_present.assert_called_once()
        pipeline.config._git_repos.materialize_git_repos.assert_not_called()
        checkout_dependencies.assert_not_called()

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_prepare_skips_build_date_when_platform_lock_exists(self, _mock_builder):
        pipeline = self._pipeline_with_mocks()
        with patch("dev_project.prepare.execute.DepsLockManager") as mock_manager_cls:
            manager = MagicMock()
            manager.has_platform_lock.return_value = True
            mock_manager_cls.return_value = manager
            with stub_prepare_service_executions():
                pipeline.prepare_project_files()
        pipeline.config._git_repos.materialize_git_repos.assert_called_once_with(
            skip_build_date=True
        )
        manager.load.assert_called_once()
        manager.enter_apply_mode.assert_called_once()

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_prepare_update_lock_collects_without_loading_lock(self, _mock_builder):
        pipeline = self._pipeline_with_mocks(update_lock=True)
        with patch("dev_project.prepare.execute.DepsLockManager") as mock_manager_cls:
            manager = MagicMock()
            mock_manager_cls.return_value = manager
            with stub_prepare_service_executions() as service_mocks:
                pipeline.prepare_project_files()
                checkout_dependencies = service_mocks[-1]
        manager.load.assert_not_called()
        manager.collect_and_save_from_config.assert_called_once()
        checkout_dependencies.assert_called_once()

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_prepare_verifies_lock_after_checkout_when_apply_mode(self, _mock_builder):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / constants.DEPS_LOCK_REL_PATH
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text(
                '{"schema_version": 1, "platform": {"url": "https://example.com/odoo.git", "commit": "abc1234"}, "dependencies": []}',
                encoding="utf-8",
            )
            pipeline = self._pipeline_with_mocks()
            pipeline.config.project_dir = tmp
            with patch("dev_project.prepare.execute.DepsLockManager") as mock_manager_cls:
                manager = MagicMock()
                manager.apply_mode = True
                mock_manager_cls.return_value = manager
                with stub_prepare_service_executions():
                    pipeline.prepare_project_files()
            manager.verify_pinned_checkout.assert_called_once()

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_prepare_rejects_update_lock_with_no_git_update(self, _mock_builder):
        pipeline = self._pipeline_with_mocks(update_lock=True, no_git_update=True)
        with self.assertRaises(PipelineError):
            pipeline.prepare_project_files()


if __name__ == "__main__":
    unittest.main()
