"""Unit tests for ProjectMaterializer."""

import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

from dev_project.errors import PipelineError
from dev_project.project_materializer import ProjectMaterializer


class ProjectMaterializerTests(unittest.TestCase):
    def _run_with_mocks(self, **args_overrides):
        args = Namespace(build_image=False, skip_start=True, **args_overrides)
        config = MagicMock()
        project_env = MagicMock()
        system_checker = MagicMock()
        materializer = ProjectMaterializer()
        materializer.run(config, project_env, system_checker, args)
        return config, project_env, system_checker

    @patch("dev_project.prepare_registry.ComposeServiceBuilder")
    def test_run_materializes_git_by_default(self, _mock_builder):
        config, project_env, system_checker = self._run_with_mocks()
        config.materialize_git_repos.assert_called_once_with(skip_build_date=False)
        config.ensure_git_repos_present.assert_not_called()
        project_env.checkout_dependencies.assert_called_once()
        system_checker.check_docker.assert_called_once()
        system_checker.check_docker_compose.assert_called_once()
        project_env.update_links.assert_called_once()

    @patch("dev_project.prepare_registry.ComposeServiceBuilder")
    def test_run_skips_git_when_no_git_update(self, _mock_builder):
        config, project_env, _system_checker = self._run_with_mocks(no_git_update=True)
        config.ensure_git_repos_present.assert_called_once()
        config.materialize_git_repos.assert_not_called()
        project_env.checkout_dependencies.assert_not_called()

    @patch("dev_project.prepare_registry.ComposeServiceBuilder")
    def test_run_rejects_update_lock_with_no_git_update(self, _mock_builder):
        materializer = ProjectMaterializer()
        with self.assertRaises(PipelineError):
            materializer.run(
                MagicMock(),
                MagicMock(),
                MagicMock(),
                Namespace(update_lock=True, no_git_update=True),
            )


if __name__ == "__main__":
    unittest.main()
