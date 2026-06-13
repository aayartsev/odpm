"""Unit tests for ProjectMaterializer."""

import unittest
from dev_project.host.cli.args import OdpmCliArgs
from unittest.mock import MagicMock, patch

from dev_project.errors import PipelineError
from dev_project.project_materializer import ProjectMaterializer
from tests.prepare_test_helpers import stub_prepare_service_executions


class ProjectMaterializerTests(unittest.TestCase):
    def _run_with_mocks(self, **args_overrides):
        args = OdpmCliArgs(build_image=False, skip_start=True, **args_overrides)
        config = MagicMock()
        project_env = MagicMock()
        system_checker = MagicMock()
        materializer = ProjectMaterializer()
        with stub_prepare_service_executions() as service_mocks:
            materializer.run(config, project_env, system_checker, args)
        return config, project_env, system_checker, service_mocks

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_run_materializes_git_by_default(self, _mock_builder):
        config, project_env, system_checker, service_mocks = self._run_with_mocks()
        (
            _map_folders,
            _dockerfile,
            _dockerignore,
            _config_file,
            _compose,
            update_links,
            checkout_dependencies,
        ) = service_mocks
        config.materialize_git_repos.assert_called_once_with(skip_build_date=False)
        config.ensure_git_repos_present.assert_not_called()
        checkout_dependencies.assert_called_once()
        system_checker.check_docker.assert_called_once()
        system_checker.check_docker_compose.assert_called_once()
        update_links.assert_called_once()

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_run_skips_git_when_no_git_update(self, _mock_builder):
        config, project_env, _system_checker, service_mocks = self._run_with_mocks(
            no_git_update=True
        )
        config.ensure_git_repos_present.assert_called_once()
        config.materialize_git_repos.assert_not_called()
        service_mocks[-1].assert_not_called()

    @patch("dev_project.compose.service_builder.ComposeServiceBuilder.build")
    def test_run_rejects_update_lock_with_no_git_update(self, _mock_builder):
        materializer = ProjectMaterializer()
        with self.assertRaises(PipelineError):
            materializer.run(
                MagicMock(),
                MagicMock(),
                MagicMock(),
                OdpmCliArgs(update_lock=True, no_git_update=True),
            )


if __name__ == "__main__":
    unittest.main()
