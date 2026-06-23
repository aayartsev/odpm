import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config.git_repos import GitRepoCoordinator
from dev_project.errors import GitError
from dev_project.git.developing_repo_materializer import DevelopingRepoMaterializer
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.project_env.links import ProjectLinks
from dev_project.symlinks import ensure_git_repo_symlink


class IncrementalRepoSymlinksTests(unittest.TestCase):
    def test_developing_materialize_creates_symlink_when_branch_switch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            repo_path = os.path.join(project_dir, "sources", "cloned_repo")
            os.makedirs(repo_path)

            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.dependencies_dirs = []
            config.symlinks_sources = []
            config.repo_odpm_json = ""
            config.arguments = OdpmCliArgs(branch="17.0", no_git_update=False)
            config.developing_project = MagicMock(
                project_path=repo_path,
                link_type=constants.GITLINK_TYPE_HTTP,
            )
            config.developing_project.build_project = MagicMock()
            config.developing_project.switch_to_branch = MagicMock(
                side_effect=GitError("branch switch failed")
            )

            materializer = DevelopingRepoMaterializer()
            with self.assertRaises(GitError):
                materializer._build_developing(config)

            link_path = os.path.join(project_dir, os.path.basename(repo_path))
            self.assertTrue(os.path.islink(link_path))
            self.assertEqual(os.readlink(link_path), repo_path)

    def test_checkout_project_creates_dependency_symlink_when_checkout_fails(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            dep_path = os.path.join(project_dir, "sources", "oca_dep")
            os.makedirs(dep_path)

            dependency = MagicMock(project_path=dep_path)
            dependency.checkout_repository = MagicMock(
                side_effect=GitError("checkout failed")
            )

            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.dependencies_dirs = [dependency]
            config.dependencies_projects = [dependency]
            config.developing_project = MagicMock()
            config.update_git_repos = True
            config.clean_git_repos = False
            config.odoo_version = "17.0"
            config.symlinks_sources = []
            config.ensure_git_repo_symlink = lambda path, *, scope: ensure_git_repo_symlink(
                config, path, scope=scope
            )
            config.ensure_developing_repo_symlinks = MagicMock()

            env = MagicMock()
            env.config = config

            with self.assertRaises(GitError):
                ProjectLinks(env).checkout_project(dependency)

            link_path = os.path.join(
                config.dependencies_dir,
                os.path.basename(dep_path),
            )
            self.assertTrue(os.path.islink(link_path))
            self.assertEqual(os.readlink(link_path), dep_path)

    @patch.object(GitRepoCoordinator, "apply_odoo_build_date_to_platform")
    def test_materialize_git_repos_creates_platform_symlink_when_build_date_fails(
        self,
        mock_apply_build_date,
    ) -> None:
        mock_apply_build_date.side_effect = GitError("build date failed")

        with tempfile.TemporaryDirectory() as project_dir:
            platform_path = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(platform_path)

            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.dependencies_dirs = []
            config.symlinks_sources = []
            config.developing_project_dir_path = ""
            config._developing_materializer.materialize_full = MagicMock()
            config.odoo_platform_project = MagicMock(project_path=platform_path)
            config.odoo_platform_project.build_project = MagicMock()
            config.ensure_git_repo_symlink = lambda path, *, scope: ensure_git_repo_symlink(
                config, path, scope=scope
            )
            config.ensure_developing_repo_symlinks = MagicMock()

            paths = MagicMock()
            paths.apply_developing_project_docker_path = MagicMock()

            coordinator = GitRepoCoordinator(config, paths=paths)

            with self.assertRaises(GitError):
                coordinator.materialize_git_repos()

            link_path = os.path.join(project_dir, os.path.basename(platform_path))
            self.assertTrue(os.path.islink(link_path))
            self.assertEqual(os.readlink(link_path), platform_path)


if __name__ == "__main__":
    unittest.main()
