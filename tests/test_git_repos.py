import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from unittest.mock import MagicMock, patch

from dev_project.config.config import Config
from dev_project.config.git_repos import GitRepoCoordinator
from dev_project.errors import ConfigError
from dev_project.git.developing_repo_materializer import DevelopingRepoMaterializer


class GitRepoCoordinatorHandleLinkTests(unittest.TestCase):
    @patch("dev_project.config.git_repos.HandleOdooProjectLink")
    def test_handle_git_link_skips_build_when_not_materializing(self, mock_link_cls):
        mock_link = MagicMock()
        mock_link_cls.return_value = mock_link
        config = MagicMock()
        config.user_env = MagicMock(path_to_ssh_key="", odoo_projects_dir="/tmp/projects")

        GitRepoCoordinator(config, paths=MagicMock()).handle_git_link(
            "git@github.com:acme/demo.git",
            materialize=False,
        )

        mock_link.build_project.assert_not_called()

    @patch("dev_project.config.git_repos.HandleOdooProjectLink")
    def test_handle_git_link_builds_when_materializing(self, mock_link_cls):
        mock_link = MagicMock()
        mock_link_cls.return_value = mock_link
        config = MagicMock()
        config.user_env = MagicMock(path_to_ssh_key="", odoo_projects_dir="/tmp/projects")

        GitRepoCoordinator(config, paths=MagicMock()).handle_git_link(
            "git@github.com:acme/demo.git",
            materialize=True,
        )

        mock_link.build_project.assert_called_once()


class GitRepoCoordinatorMaterializeTests(unittest.TestCase):
    def _coordinator(self, config=None):
        if config is None:
            config = MagicMock()
            config.developing_project = MagicMock()
            config.odoo_platform_project = MagicMock()
            config.arguments = OdpmCliArgs(branch=None)
            config._developing_materializer = DevelopingRepoMaterializer()
            config.odoo_build_date = "20240101"
            config.odoo_version = "17.0"
        paths = MagicMock()
        return GitRepoCoordinator(config, paths=paths), config, paths

    def test_materialize_git_repos_builds_developing_and_platform(self):
        coordinator, config, paths = self._coordinator()

        coordinator.materialize_git_repos()

        config.developing_project.build_project.assert_called_once()
        config.odoo_platform_project.build_project.assert_called_once()
        config.odoo_platform_project.apply_build_date.assert_called_once_with(
            "20240101",
            "17.0",
        )
        paths.apply_developing_project_docker_path.assert_called_once()

    def test_materialize_git_repos_skips_build_date_when_requested(self):
        coordinator, config, _paths = self._coordinator()

        coordinator.materialize_git_repos(skip_build_date=True)

        config.odoo_platform_project.build_project.assert_called_once()
        config.odoo_platform_project.apply_build_date.assert_not_called()

    def test_materialize_git_repos_skips_developing_rebuild_when_already_materialized(
        self,
    ):
        coordinator, config, _paths = self._coordinator()
        config.arguments = OdpmCliArgs(branch="17.0")
        materializer = DevelopingRepoMaterializer()
        materializer._developing_repo_materialized = True
        config._developing_materializer = materializer

        coordinator.materialize_git_repos()

        config.developing_project.build_project.assert_not_called()
        config.developing_project.switch_to_branch.assert_not_called()
        config.odoo_platform_project.build_project.assert_called_once()


class GitRepoCoordinatorEnsurePresentTests(unittest.TestCase):
    def test_ensure_git_repos_present_raises_when_directories_missing(self):
        config = MagicMock()
        config.odoo_src_dir = "/missing/platform"
        config.developing_project_dir_path = "/missing/dev"

        with self.assertRaises(ConfigError):
            GitRepoCoordinator(config, paths=MagicMock()).ensure_git_repos_present()

    def test_ensure_git_repos_present_passes_when_directories_exist(self):
        with tempfile.TemporaryDirectory() as platform_dir, tempfile.TemporaryDirectory() as dev_dir:
            config = MagicMock()
            config.odoo_src_dir = platform_dir
            config.developing_project_dir_path = dev_dir

            GitRepoCoordinator(config, paths=MagicMock()).ensure_git_repos_present()


class GitRepoCoordinatorPlatformSourcesTests(unittest.TestCase):
    def test_get_platform_sources_rebinds_platform_and_applies_build_date(self):
        config = MagicMock()
        config.odoo_build_date = "20240501"
        config.odoo_version = "19.0"
        bind_platform_link = MagicMock()

        GitRepoCoordinator(
            config,
            paths=MagicMock(),
            bind_platform_link=bind_platform_link,
        ).get_platform_sources()

        bind_platform_link.assert_called_once_with(config)
        config.odoo_platform_project.build_project.assert_called_once()
        config.odoo_platform_project.apply_build_date.assert_called_once_with(
            "20240501",
            "19.0",
        )

    def test_get_platform_sources_requires_bind_platform_link(self):
        config = MagicMock()

        with self.assertRaises(ConfigError):
            GitRepoCoordinator(config, paths=MagicMock()).get_platform_sources()


class ConfigGitRepoDelegationTests(unittest.TestCase):
    @patch("dev_project.config.git_repos.HandleOdooProjectLink")
    def test_config_handle_git_link_uses_context_coordinator(self, mock_link_cls):
        from dev_project.config.bootstrap_context import ConfigBootstrapContext

        mock_link = MagicMock()
        mock_link_cls.return_value = mock_link
        config = Config.__new__(Config)
        config.user_env = MagicMock(path_to_ssh_key="", odoo_projects_dir="/tmp/projects")
        ctx = ConfigBootstrapContext(config, bind_platform_link=MagicMock())
        config._git_repos = ctx.git_repos

        result = config.handle_git_link(
            "git@github.com:acme/demo.git",
            materialize=True,
        )

        mock_link.build_project.assert_called_once()
        self.assertIs(result, mock_link)


if __name__ == "__main__":
    unittest.main()
