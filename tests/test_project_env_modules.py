import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants, translations
from dev_project.errors import PipelineError
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.base_image import BaseImageBuilder
from dev_project.project_env.ci_image import CiImageBuilder
from dev_project.project_env.compose import ComposeGenerator
from dev_project.project_dir_manager import ProjectDirManager
from dev_project.scenario_policy import ScenarioPolicy


class ProjectTemplatesTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _make_manager(self, project_dir: str) -> ProjectDirManager:
        os.makedirs(
            os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
            exist_ok=True,
        )
        return ProjectDirManager(
            project_dir,
            MagicMock(init=False, odoo_git_link=None),
            self._program_dir(),
        )

    def _make_env(self, project_dir: str) -> CreateProjectEnvironment:
        config = MagicMock()
        config.project_dir = project_dir
        config.project_dockerignore_template_path = os.path.join(
            project_dir,
            constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        return CreateProjectEnvironment(config)

    def test_generate_dockerignore_writes_managed_file(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            manager.rebuild_dockerignore_template()
            env = self._make_env(project_dir)
            env._templates.generate_dockerignore()

            dockerignore = Path(project_dir) / constants.DOCKERIGNORE
            self.assertTrue(dockerignore.is_file())
            content = dockerignore.read_text(encoding="utf-8")
            self.assertIn(
                translations.get_translation(translations.DO_NOT_CHANGE_FILE),
                content,
            )
            self.assertIn("**/.git", content)

    def test_get_vscode_dir_path_creates_directory(self):
        with tempfile.TemporaryDirectory() as project_dir:
            env = self._make_env(project_dir)
            vscode_dir = env._templates.get_vscode_dir_path()
            self.assertTrue(os.path.isdir(vscode_dir))
            self.assertEqual(vscode_dir, os.path.join(project_dir, ".vscode"))


class ComposeGeneratorTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _make_env(self, project_dir: str) -> CreateProjectEnvironment:
        policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = policy
        config.odoo_image_name = "odoo-dev:test"
        config.start_string = '["python3", "odoo-bin"]'
        config.compose_file_version = "3.8"
        config.postgres_version = "16"
        config.postgres_data_local_storage = "/tmp/postgres-data"
        config.pd_manager = MagicMock()
        user_env = MagicMock()
        user_env.postgres_port = None
        user_env.debugger_port = None
        user_env.odoo_port = None
        user_env.gevent_port = None
        config.user_env = user_env
        env = CreateProjectEnvironment(config)
        env.mapped_folders = []
        return env

    def test_generate_docker_compose_file_writes_compose_yml(self):
        with tempfile.TemporaryDirectory() as project_dir:
            template_dest = os.path.join(
                project_dir,
                constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
            )
            os.makedirs(os.path.dirname(template_dest), exist_ok=True)
            shutil.copy(
                os.path.join(self._program_dir(), "dev_project", "templates", "docker-compose.yml"),
                template_dest,
            )
            env = self._make_env(project_dir)
            env._compose.generate_docker_compose_file()

            compose_path = Path(project_dir) / "docker-compose.yml"
            self.assertTrue(compose_path.is_file())
            content = compose_path.read_text(encoding="utf-8")
            self.assertIn("odoo-dev:test", content)
            self.assertIn(
                translations.get_translation(translations.DO_NOT_CHANGE_FILE),
                content,
            )


class BaseImageBuilderTests(unittest.TestCase):
    def _builder(self) -> BaseImageBuilder:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.dockerfile_path = "/tmp/project/Dockerfile"
        config.odoo_image_name = "odoo-base:test"
        config.arch = "amd64"
        env = MagicMock()
        env.config = config
        return BaseImageBuilder(env)

    @patch("dev_project.project_env.base_image.run_checked")
    def test_base_image_exists_when_repository_matches(self, mock_checked):
        mock_checked.return_value = MagicMock(
            stdout='{"Repository":"odoo-base:test","Tag":"latest"}\n'
        )
        self.assertTrue(self._builder().base_image_exists())

    @patch("dev_project.project_env.base_image.run_logged", return_value=1)
    @patch("dev_project.project_env.base_image.os.chdir")
    def test_build_base_image_raises_pipeline_error_on_failure(
        self, _mock_chdir, _mock_logged
    ):
        with self.assertRaises(PipelineError) as ctx:
            self._builder().build_base_image()
        self.assertEqual(ctx.exception.exit_code, 1)

    @patch.object(BaseImageBuilder, "build_base_image")
    @patch.object(BaseImageBuilder, "base_image_exists", return_value=False)
    def test_ensure_base_image_builds_when_missing(
        self, _mock_exists, mock_build
    ):
        self._builder().ensure_base_image()
        mock_build.assert_called_once()


class CiImageBuilderPipelineTests(unittest.TestCase):
    def _builder(self) -> CiImageBuilder:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.odoo_ci_image_name = "odoo-ci:test"
        config.odoo_image_name = "odoo-base:test"
        config.arch = "amd64"
        config.ci_build_context_dir = "/tmp/project/.odpm/ci-build-context"
        env = MagicMock()
        env.config = config
        env._base_image = MagicMock()
        env.mapped_folders = []
        return CiImageBuilder(env)

    @patch("dev_project.project_env.ci_image.run_logged", return_value=2)
    @patch.object(CiImageBuilder, "generate_ci_dockerfile", return_value="/ctx/Dockerfile.ci")
    @patch.object(CiImageBuilder, "prepare_ci_build_context")
    def test_build_ci_image_raises_pipeline_error_on_failure(
        self, _mock_prepare, _mock_dockerfile, _mock_logged
    ):
        builder = self._builder()
        with self.assertRaises(PipelineError) as ctx:
            builder.build_ci_image()
        self.assertEqual(ctx.exception.exit_code, 2)
        builder.env._base_image.ensure_base_image.assert_called_once()


if __name__ == "__main__":
    unittest.main()
