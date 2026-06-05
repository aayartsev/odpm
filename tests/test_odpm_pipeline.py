import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.odpm_pipeline import OdpmPipeline, PipelineError
from dev_project.scenario_policy import ScenarioPolicy


class OdpmPipelinePolicyTests(unittest.TestCase):
    def _pipeline(self, **args_overrides) -> OdpmPipeline:
        args = Namespace(**{"build_image": False, "skip_start": False, **args_overrides})
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        return pipeline

    def test_handle_build_image_rejects_non_ci_policy(self):
        pipeline = self._pipeline(build_image=True)
        pipeline.config.policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        )
        with self.assertRaises(PipelineError) as ctx:
            pipeline.handle_build_image()
        self.assertEqual(ctx.exception.exit_code, 1)
        pipeline.project_environment.build_ci_image.assert_not_called()

    def test_handle_build_image_runs_for_ci_policy(self):
        pipeline = self._pipeline(build_image=True)
        pipeline.config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        self.assertTrue(pipeline.handle_build_image())
        pipeline.project_environment.build_ci_image.assert_called_once()

    def test_configure_vscode_skipped_when_policy_says_so(self):
        pipeline = self._pipeline()
        pipeline.config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        pipeline.configure_vscode()
        pipeline.project_environment.update_vscode_debugger_launcher.assert_not_called()
        pipeline.project_environment.generate_vscode_settings_json.assert_not_called()

    def test_configure_vscode_runs_for_developer_policy(self):
        pipeline = self._pipeline()
        pipeline.config.policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        )
        pipeline.configure_vscode()
        pipeline.project_environment.update_vscode_debugger_launcher.assert_called_once()
        pipeline.project_environment.generate_vscode_settings_json.assert_called_once()

    def test_start_string_builder_uses_same_policy_instance(self):
        config = MagicMock()
        policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        config.policy = policy
        config.arguments = Namespace(
            d=None,
            translate=None,
            pip_install=False,
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

        from dev_project.host_start_string_builder import StartStringBuilder

        builder = StartStringBuilder(config)
        builder.build()
        self.assertIs(builder.policy, policy)


class OdpmPipelineComposeTests(unittest.TestCase):
    def test_build_compose_up_argv_force_recreate_explicit(self):
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        pipeline = OdpmPipeline(Namespace(), "/opt/odpm")
        self.assertEqual(
            pipeline.build_compose_up_argv(config, force_recreate=True),
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
        pipeline = OdpmPipeline(Namespace(), "/opt/odpm")
        self.assertEqual(
            pipeline.build_compose_up_argv(config, force_recreate=False),
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
        pipeline = OdpmPipeline(Namespace(), "/opt/odpm")
        self.assertEqual(
            pipeline.build_compose_up_argv(config, force_recreate=True),
            [
                "docker-compose",
                "up",
                "--no-log-prefix",
                "--abort-on-container-exit",
                "--force-recreate",
            ],
        )

    @patch(
        "dev_project.odpm_pipeline.should_force_recreate_compose",
        return_value=True,
    )
    def test_build_compose_up_argv_auto_detects_force_recreate(self, _mock_should):
        config = MagicMock()
        config.docker_compose_command = "docker compose"
        config.no_log_prefix = False
        pipeline = OdpmPipeline(Namespace(), "/opt/odpm")
        argv = pipeline.build_compose_up_argv(config)
        self.assertIn("--force-recreate", argv)

    @patch(
        "dev_project.odpm_pipeline.should_force_recreate_compose",
        return_value=False,
    )
    def test_start_containers_uses_subprocess(self, _mock_should):
        pipeline = OdpmPipeline(Namespace(), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.config.project_dir = "/tmp/project"
        pipeline.config.docker_compose_command = "docker compose"
        pipeline.config.no_log_prefix = False
        with patch("dev_project.odpm_pipeline.run_logged", return_value=0) as mock_run:
            pipeline.start_containers()
        mock_run.assert_called_once_with(
            ["docker", "compose", "up", "--abort-on-container-exit"],
            cwd="/tmp/project",
        )

    @patch(
        "dev_project.odpm_pipeline.should_force_recreate_compose",
        return_value=False,
    )
    def test_start_containers_raises_pipeline_error_on_compose_failure(
        self, _mock_should
    ):
        pipeline = OdpmPipeline(Namespace(), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.config.project_dir = "/tmp/project"
        pipeline.config.docker_compose_command = "docker compose"
        pipeline.config.no_log_prefix = False
        with patch("dev_project.odpm_pipeline.run_logged", return_value=17):
            with self.assertRaises(PipelineError) as ctx:
                pipeline.start_containers()
        self.assertEqual(ctx.exception.exit_code, 17)


class OdpmPipelineRunTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.OdpmPipeline.start_containers")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.configure_vscode")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.handle_build_image", return_value=False)
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_skips_compose_when_skip_start(
        self,
        mock_setup,
        mock_prepare,
        mock_build_image,
        mock_vscode,
        mock_start,
    ):
        args = Namespace(build_image=False, skip_start=True)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.config.project_dir = "/tmp/project"

        with patch("dev_project.odpm_pipeline.os.chdir"):
            pipeline.run()

        mock_start.assert_not_called()
        mock_vscode.assert_called_once()

    @patch("dev_project.odpm_pipeline.OdpmPipeline.start_containers")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.configure_vscode")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.handle_build_image", return_value=True)
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_stops_after_build_image(
        self,
        mock_setup,
        mock_prepare,
        mock_build_image,
        mock_vscode,
        mock_start,
    ):
        args = Namespace(build_image=True, skip_start=False)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.config.project_dir = "/tmp/project"

        with patch("dev_project.odpm_pipeline.os.chdir"):
            pipeline.run()

        mock_vscode.assert_not_called()
        mock_start.assert_not_called()

    @patch("dev_project.odpm_pipeline.sys.exit")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.prepare_project_files")
    @patch("dev_project.odpm_pipeline.OdpmPipeline.setup")
    def test_run_exits_on_pipeline_error(
        self, mock_setup, mock_prepare, mock_exit
    ):
        pipeline = OdpmPipeline(Namespace(build_image=True), "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.config.policy = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        )
        pipeline.project_environment = MagicMock()
        with patch.object(
            pipeline,
            "handle_build_image",
            side_effect=PipelineError("forbidden", exit_code=1),
        ):
            pipeline.run()
        mock_exit.assert_called_once_with(1)


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

        pipeline = OdpmPipeline(Namespace(build_image=False, skip_start=False), "/opt/odpm")
        pipeline.setup()

        self.assertIs(pipeline.config, mock_config)
        self.assertIs(pipeline.project_environment, mock_project_env)
        self.assertIs(pipeline.system_checker, mock_checker)
        mock_config_cls.assert_called_once()
        mock_project_env_cls.assert_called_once_with(mock_config)
        mock_checker_cls.assert_called_once_with(mock_config, mock_project_env)


class OdpmPipelinePrepareTests(unittest.TestCase):
    def _pipeline_with_mocks(self, **args_overrides) -> OdpmPipeline:
        args = Namespace(build_image=False, skip_start=True, **args_overrides)
        pipeline = OdpmPipeline(args, "/opt/odpm")
        pipeline.config = MagicMock()
        pipeline.project_environment = MagicMock()
        pipeline.system_checker = MagicMock()
        return pipeline

    @patch("dev_project.odpm_pipeline.StartStringBuilder")
    def test_prepare_calls_materialize_git_repos_by_default(self, _mock_builder):
        pipeline = self._pipeline_with_mocks()
        pipeline.prepare_project_files()
        pipeline.config.materialize_git_repos.assert_called_once()
        pipeline.config.ensure_git_repos_present.assert_not_called()
        pipeline.project_environment.checkout_dependencies.assert_called_once()

    @patch("dev_project.odpm_pipeline.StartStringBuilder")
    def test_prepare_skips_git_when_no_git_update(self, _mock_builder):
        pipeline = self._pipeline_with_mocks(no_git_update=True)
        pipeline.prepare_project_files()
        pipeline.config.ensure_git_repos_present.assert_called_once()
        pipeline.config.materialize_git_repos.assert_not_called()
        pipeline.project_environment.checkout_dependencies.assert_not_called()


if __name__ == "__main__":
    unittest.main()
