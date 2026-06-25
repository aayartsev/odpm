import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.translations import _
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.errors import PipelineError
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.base_image import BaseImageBuilder
from dev_project.project_env.ci_image import CiImageBuilder
from dev_project.project_env.services import (
    BaseImageService,
    CiImageBuildService,
    VscodeConfigurator,
)
from dev_project.project_dir_manager import ProjectDirManager
from dev_project.scenario_policy import ScenarioPolicy


class ProjectTemplatesTests(unittest.TestCase):
    def test_create_project_environment_does_not_set_config_project_env(self):
        class ConfigStub:
            user_env = MagicMock()

        config = ConfigStub()
        CreateProjectEnvironment(config)  # type: ignore[arg-type]
        self.assertFalse(hasattr(config, "project_env"))

    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _make_manager(self, project_dir: str) -> ProjectDirManager:
        os.makedirs(
            os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
            exist_ok=True,
        )
        return ProjectDirManager(
            project_dir,
            OdpmCliArgs(),
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
                _('Do not change this file, its content is generating automatically'),
                content,
            )
            self.assertIn("**/.git", content)

    def test_get_vscode_dir_path_creates_directory(self):
        with tempfile.TemporaryDirectory() as project_dir:
            env = self._make_env(project_dir)
            vscode_dir = VscodeConfigurator(env).get_vscode_dir_path()
            self.assertTrue(os.path.isdir(vscode_dir))
            self.assertEqual(vscode_dir, os.path.join(project_dir, ".vscode"))

    def test_generate_dockerfile_uses_policy_runtime_identity(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            manager.rebuild_dockerfile_template(
                docker_template_filename="debian_13_dockerfile"
            )
            template_path = os.path.join(
                project_dir, ".odpm", "debian_13_dockerfile"
            )
            policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            config = MagicMock()
            config.project_dir = project_dir
            config.project_dockerfile_template_path = template_path
            config.policy = policy
            config.arch = "amd64"
            config.python_version = "3.12"
            config.distro_name = "debian"
            config.distro_version = "13"
            config.distro_version_codename = constants.DISTRO_INFO["debian"]["13"]
            env = CreateProjectEnvironment(config)
            env._templates.generate_dockerfile()

            dockerfile = Path(project_dir, constants.DOCKERFILE).read_text(
                encoding="utf-8"
            )
            self.assertIn(f"ARG USER_UID={policy.runtime_unix_uid()}", dockerfile)
            self.assertIn(f"ARG USER_GID={policy.runtime_unix_gid()}", dockerfile)
            self.assertIn(f"ARG USER_NAME={policy.runtime_unix_user()}", dockerfile)

    def test_generate_dockerfile_ci_uses_container_identity(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            manager.rebuild_dockerfile_template(
                docker_template_filename="debian_13_dockerfile"
            )
            template_path = os.path.join(
                project_dir, ".odpm", "debian_13_dockerfile"
            )
            policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            config = MagicMock()
            config.project_dir = project_dir
            config.project_dockerfile_template_path = template_path
            config.policy = policy
            config.arch = "amd64"
            config.python_version = "3.12"
            config.distro_name = "debian"
            config.distro_version = "13"
            config.distro_version_codename = constants.DISTRO_INFO["debian"]["13"]
            env = CreateProjectEnvironment(config)
            env._templates.generate_dockerfile()

            dockerfile = Path(project_dir, constants.DOCKERFILE).read_text(
                encoding="utf-8"
            )
            self.assertIn(f"ARG USER_UID={constants.CONTAINER_USER_UID}", dockerfile)
            self.assertIn(f"ARG USER_NAME={constants.CONTAINER_USER}", dockerfile)


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

    @patch("dev_project.project_env.base_image.run_or_raise")
    def test_base_image_exists_when_image_inspect_succeeds(self, mock_run_or_raise):
        mock_run_or_raise.return_value = MagicMock(stdout="", stderr="")
        self.assertTrue(self._builder().base_image_exists())
        mock_run_or_raise.assert_called_once_with(
            ["docker", "image", "inspect", "odoo-base:test"]
        )

    @patch("dev_project.project_env.base_image.run_or_raise")
    def test_base_image_exists_returns_false_when_inspect_fails(self, mock_run_or_raise):
        from dev_project.errors import SubprocessError

        mock_run_or_raise.side_effect = SubprocessError(
            "missing",
            argv=["docker", "image", "inspect", "odoo-base:test"],
            returncode=1,
        )
        self.assertFalse(self._builder().base_image_exists())

    @patch("dev_project.project_env.base_image.run_logged", return_value=1)
    def test_build_base_image_raises_pipeline_error_on_failure(self, mock_logged):
        with self.assertRaises(PipelineError) as ctx:
            self._builder().build_base_image()
        self.assertEqual(ctx.exception.exit_code, 1)

    @patch("dev_project.project_env.base_image.run_logged", return_value=0)
    def test_build_base_image_uses_project_dir_as_cwd(self, mock_logged):
        builder = self._builder()
        builder.build_base_image()
        mock_logged.assert_called_once()
        self.assertEqual(mock_logged.call_args.kwargs["cwd"], builder.config.project_dir)

    @patch("dev_project.project_env.base_image.write_base_image_identity")
    @patch.object(BaseImageBuilder, "build_base_image")
    @patch.object(BaseImageBuilder, "base_image_exists", return_value=False)
    @patch(
        "dev_project.project_env.base_image.base_image_identity_matches",
        return_value=False,
    )
    def test_ensure_base_image_builds_when_missing(
        self, _mock_matches, _mock_exists, mock_build, mock_write_identity
    ):
        self._builder().ensure_base_image()
        mock_build.assert_called_once()
        mock_write_identity.assert_called_once()

    @patch("dev_project.project_env.base_image.write_base_image_identity")
    @patch.object(BaseImageBuilder, "build_base_image")
    @patch.object(BaseImageBuilder, "base_image_exists", return_value=True)
    @patch(
        "dev_project.project_env.base_image.base_image_identity_matches",
        return_value=False,
    )
    @patch(
        "dev_project.project_env.base_image.read_base_image_identity",
        return_value=None,
    )
    def test_ensure_base_image_logs_missing_stamp(
        self,
        _mock_read,
        _mock_matches,
        _mock_exists,
        mock_build,
        _mock_write_identity,
    ):
        with self.assertLogs("dev_project.project_env.base_image", level="INFO") as logs:
            self._builder().ensure_base_image()
        self.assertTrue(
            any("missing identity stamp" in message for message in logs.output)
        )
        mock_build.assert_called_once()

    @patch("dev_project.project_env.base_image.write_base_image_identity")
    @patch.object(BaseImageBuilder, "build_base_image")
    @patch.object(BaseImageBuilder, "base_image_exists", return_value=True)
    @patch(
        "dev_project.project_env.base_image.base_image_identity_matches",
        return_value=False,
    )
    @patch(
        "dev_project.project_env.base_image.expected_base_image_identity",
        return_value={
            "user": "odoo",
            "uid": "1000",
            "gid": "1000",
            "base_image_profile": "full",
            "dockerfile_sha256": "abc",
        },
    )
    @patch(
        "dev_project.project_env.base_image.read_base_image_identity",
        return_value={
            "user": "odoo",
            "uid": "9999",
            "gid": "9999",
            "base_image_profile": "full",
            "dockerfile_sha256": "abc",
        },
    )
    def test_ensure_base_image_logs_identity_mismatch(
        self,
        _mock_read,
        _mock_expected,
        _mock_matches,
        _mock_exists,
        mock_build,
        _mock_write_identity,
    ):
        with self.assertLogs("dev_project.project_env.base_image", level="INFO") as logs:
            self._builder().ensure_base_image()
        self.assertTrue(
            any("runtime Unix identity changed" in message for message in logs.output)
        )
        mock_build.assert_called_once()

    @patch("dev_project.project_env.base_image.write_base_image_identity")
    @patch.object(BaseImageBuilder, "build_base_image")
    @patch.object(BaseImageBuilder, "base_image_exists", return_value=True)
    @patch(
        "dev_project.project_env.base_image.base_image_identity_matches",
        return_value=False,
    )
    @patch(
        "dev_project.project_env.base_image.read_base_image_identity",
        return_value={
            "user": "odoo",
            "uid": "9999",
            "gid": "9999",
            "base_image_profile": "full",
            "dockerfile_sha256": "abc",
        },
    )
    def test_ensure_base_image_rebuilds_when_identity_mismatch(
        self, _mock_read, _mock_matches, _mock_exists, mock_build, mock_write_identity
    ):
        self._builder().ensure_base_image()
        mock_build.assert_called_once()
        mock_write_identity.assert_called_once()

    @patch.object(BaseImageBuilder, "build_base_image")
    @patch.object(BaseImageBuilder, "base_image_exists", return_value=True)
    @patch(
        "dev_project.project_env.base_image.base_image_identity_matches",
        return_value=True,
    )
    def test_ensure_base_image_skips_when_image_and_identity_match(
        self, _mock_matches, _mock_exists, mock_build
    ):
        self._builder().ensure_base_image()
        mock_build.assert_not_called()


class BaseImageServiceTests(unittest.TestCase):
    @patch.object(BaseImageBuilder, "ensure_base_image")
    def test_ensure_base_image_delegates_to_builder(self, mock_ensure):
        config = MagicMock()
        env = MagicMock()
        env.config = config
        BaseImageService(env).ensure_base_image()
        mock_ensure.assert_called_once()


class CiImageBuildServiceTests(unittest.TestCase):
    def _service(self) -> CiImageBuildService:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.odoo_ci_image_name = "odoo-ci:test"
        config.odoo_image_name = "odoo-base:test"
        config.arch = "amd64"
        config.ci_build_context_dir = "/tmp/project/.odpm/ci-build-context"
        env = MagicMock()
        env.config = config
        env.mapped_folders = []
        return CiImageBuildService(env)

    @patch("dev_project.project_env.ci_image.BaseImageService")
    @patch("dev_project.project_env.ci_image.run_logged", return_value=2)
    @patch.object(CiImageBuilder, "generate_ci_dockerfile", return_value="/ctx/Dockerfile.ci")
    @patch.object(CiImageBuilder, "prepare_ci_build_context")
    def test_build_ci_image_raises_pipeline_error_on_failure(
        self,
        _mock_prepare,
        _mock_dockerfile,
        _mock_logged,
        mock_base_image_service,
    ):
        service = self._service()
        with self.assertRaises(PipelineError) as ctx:
            service.build_ci_image()
        self.assertEqual(ctx.exception.exit_code, 2)
        mock_base_image_service.assert_called_once_with(service.env)
        mock_base_image_service.return_value.ensure_base_image.assert_called_once()


if __name__ == "__main__":
    unittest.main()
