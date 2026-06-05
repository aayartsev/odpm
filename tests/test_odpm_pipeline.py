import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.odpm_pipeline import OdpmPipeline
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
        with patch(
            "dev_project.odpm_pipeline.sys.exit", side_effect=SystemExit(1)
        ) as mock_exit:
            with self.assertRaises(SystemExit):
                pipeline.handle_build_image()
        mock_exit.assert_called_once_with(1)
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
        self.assertIs(builder.policy, policy)


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


if __name__ == "__main__":
    unittest.main()
