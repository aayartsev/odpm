import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants, translations
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.compose import ComposeGenerator
from dev_project.project_env.types import MappedPath
from dev_project.start_command import ComposeOdooService
from dev_project.scenario_policy import ScenarioPolicy


class ComposeGeneratorPolicyTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _copy_compose_template(self, project_dir: str) -> None:
        template_dest = os.path.join(
            project_dir,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        os.makedirs(os.path.dirname(template_dest), exist_ok=True)
        shutil.copy(
            os.path.join(
                self._program_dir(), "dev_project", "templates", "docker-compose.yml"
            ),
            template_dest,
        )

    def _make_env(self, project_dir: str, scenario: str) -> CreateProjectEnvironment:
        policy = ScenarioPolicy.from_scenario(scenario)
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = policy
        config.odoo_image_name = "odoo-base:dev"
        config.odoo_ci_image_name = "odoo-ci:19"
        config.compose_service = ComposeOdooService(
            working_dir="/home/odoo",
            include_runtime_config=policy.mount_runtime_config_from_host(),
            command=[
                "python3",
                "-m",
                constants.RUN_ODOO_ENTRYPOINT,
                "--",
                "/home/odoo/odoo/odoo-bin",
            ],
        )
        config.compose_file_version = "3.8"
        config.postgres_version = "16"
        config.postgres_data_local_storage = "/tmp/postgres-data"
        config.pd_manager = MagicMock()
        user_env = MagicMock()
        user_env.postgres_port = 15432
        user_env.debugger_port = 5678
        user_env.odoo_port = 8069
        user_env.gevent_port = 8072
        config.user_env = user_env
        env = CreateProjectEnvironment(config)
        env.mapped_folders = [
            MappedPath(local="/tmp/local-addons", docker="/home/odoo/extra-addons")
        ]
        return env

    def _compose_content(self, project_dir: str, scenario: str) -> str:
        self._copy_compose_template(project_dir)
        env = self._make_env(project_dir, scenario)
        env._compose.generate_docker_compose_file()
        return (Path(project_dir) / "docker-compose.yml").read_text(encoding="utf-8")

    def test_developer_compose_includes_debugger_port_and_volumes(self):
        with tempfile.TemporaryDirectory() as project_dir:
            content = self._compose_content(project_dir, constants.DEVELOPER_SCENARIO)
            self.assertIn("odoo-base:dev", content)
            self.assertIn("5678:5678", content)
            self.assertIn("15432:5432", content)
            self.assertNotIn("127.0.0.1:15432:5432", content)
            self.assertIn("/tmp/local-addons:/home/odoo/extra-addons:Z", content)
            self.assertIn("volumes:", content)

    def test_server_compose_binds_postgres_localhost_without_debugger(self):
        with tempfile.TemporaryDirectory() as project_dir:
            content = self._compose_content(project_dir, constants.SERVER_SCENARIO)
            self.assertIn("odoo-base:dev", content)
            self.assertIn("127.0.0.1:15432:5432", content)
            self.assertNotIn("5678:5678", content)
            self.assertIn("/tmp/local-addons:/home/odoo/extra-addons:Z", content)
            policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
            self.assertIn(f"user: {policy.runtime_unix_user()}", content)

    def test_ci_compose_uses_ci_image_without_volumes_or_debugger(self):
        with tempfile.TemporaryDirectory() as project_dir:
            content = self._compose_content(project_dir, constants.CI_SCENARIO)
            self.assertIn("odoo-ci:19", content)
            self.assertNotIn("odoo-base:dev", content)
            self.assertIn("127.0.0.1:15432:5432", content)
            self.assertNotIn("5678:5678", content)
            self.assertNotIn("/tmp/local-addons:/home/odoo/extra-addons:Z", content)
            self.assertIn(f"user: {constants.CONTAINER_USER}", content)

    def test_developer_compose_user_matches_host_identity(self):
        policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        expected_user = policy.runtime_unix_user()
        with tempfile.TemporaryDirectory() as project_dir:
            content = self._compose_content(project_dir, constants.DEVELOPER_SCENARIO)
            self.assertIn(f"user: {expected_user}", content)
            if expected_user != constants.CONTAINER_USER:
                self.assertNotIn(f"user: {constants.CONTAINER_USER}", content)

    def test_compose_uses_exec_form_without_bash_for_standard_path(self):
        with tempfile.TemporaryDirectory() as project_dir:
            content = self._compose_content(project_dir, constants.DEVELOPER_SCENARIO)
            self.assertIn("working_dir: /home/odoo", content)
            self.assertIn(
                f"{constants.ODPM_CONFIG_PATH_ENV}={constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}",
                content,
            )
            runtime_config_host = os.path.join(
                project_dir, constants.ODPM_RUNTIME_CONFIG_REL_PATH
            )
            self.assertIn(
                f"{runtime_config_host}:{constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}:ro",
                content,
            )
            self.assertNotIn("ODPM_CONFIG_B64=", content)
            self.assertIn(f"- {constants.RUN_ODOO_ENTRYPOINT}", content)
            self.assertNotIn("bash -c", content)
            self.assertIn("    command:", content)

    def test_ci_compose_omits_host_runtime_config_volume(self):
        with tempfile.TemporaryDirectory() as project_dir:
            content = self._compose_content(project_dir, constants.CI_SCENARIO)
            runtime_config_host = os.path.join(
                project_dir, constants.ODPM_RUNTIME_CONFIG_REL_PATH
            )
            self.assertNotIn(
                f"{runtime_config_host}:{constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}:ro",
                content,
            )
            self.assertNotIn(
                f"{constants.ODPM_CONFIG_PATH_ENV}={constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}",
                content,
            )
            self.assertNotIn("/tmp/local-addons:/home/odoo/extra-addons:Z", content)

    @patch("dev_project.project_env.compose.template_needs_upgrade", return_value=True)
    def test_ensure_compose_template_current_rebuilds_legacy_template(
        self, _mock_needs_upgrade
    ):
        with tempfile.TemporaryDirectory() as project_dir:
            self._copy_compose_template(project_dir)
            env = self._make_env(project_dir, constants.DEVELOPER_SCENARIO)
            template_path = os.path.join(
                project_dir,
                constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
            )
            ComposeGenerator(env)._ensure_compose_template_current(template_path)
            env.config.pd_manager.rebuild_docker_compose_template.assert_called_once()


if __name__ == "__main__":
    unittest.main()
