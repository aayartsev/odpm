import os
import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config.config import Config
from dev_project.git.developing_repo_materializer import DevelopingRepoMaterializer
from dev_project.config.state import DockerLayoutState, ProjectSettingsState, UserSettingsState


class DevelopingRepoMaterializerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.materializer = DevelopingRepoMaterializer()

    def test_materialize_for_odpm_json_clones_remote_git(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = Config.__new__(Config)
            config._user = UserSettingsState()
            config._project = ProjectSettingsState()
            config._docker = DockerLayoutState()
            config.project_dir = project_dir
            config.arguments = OdpmCliArgs(branch="17.0", no_git_update=False)
            config.developing_project = MagicMock(
                project_path=os.path.join(project_dir, "cloned_repo"),
                link_type=constants.GITLINK_TYPE_HTTP,
            )
            config.skip_git_update = lambda: False

            materialized = self.materializer.materialize_for_odpm_json(config)

            config.developing_project.build_project.assert_called_once()
            config.developing_project.switch_to_branch.assert_called_once_with("17.0")
            self.assertTrue(materialized)
            self.assertTrue(self.materializer.developing_repo_materialized)

    @patch("dev_project.git.developing_repo_materializer.ensure_developing_repo_symlinks")
    def test_materialize_for_odpm_json_checkouts_branch_when_odpm_json_exists(
        self, mock_symlinks
    ):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "cloned_repo")
            os.makedirs(dev_path)
            odpm_path = os.path.join(dev_path, constants.PROJECT_CONFIG_FILE_NAME)
            Path(odpm_path).write_text('{"odpm_version": "3.0"}', encoding="utf-8")

            config = Config.__new__(Config)
            config._user = UserSettingsState()
            config._project = ProjectSettingsState()
            config._docker = DockerLayoutState()
            config.project_dir = project_dir
            config.arguments = OdpmCliArgs(branch="17.0-dev", no_git_update=False)
            config.developing_project = MagicMock(
                project_path=dev_path,
                link_type=constants.GITLINK_TYPE_GIT,
            )
            config.skip_git_update = lambda: False

            materialized = self.materializer.materialize_for_odpm_json(config)

            config.developing_project.build_project.assert_called_once()
            config.developing_project.switch_to_branch.assert_called_once_with(
                "17.0-dev"
            )
            mock_symlinks.assert_called_once_with(config)
            self.assertTrue(materialized)
            self.assertTrue(self.materializer.developing_repo_materialized)

    def test_materialize_for_odpm_json_skips_when_odpm_json_exists(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "cloned_repo")
            os.makedirs(dev_path)
            odpm_path = os.path.join(dev_path, constants.PROJECT_CONFIG_FILE_NAME)
            Path(odpm_path).write_text("{}", encoding="utf-8")

            config = Config.__new__(Config)
            config._user = UserSettingsState()
            config._project = ProjectSettingsState()
            config._docker = DockerLayoutState()
            config.project_dir = project_dir
            config.arguments = OdpmCliArgs(branch=None, no_git_update=False)
            config.developing_project = MagicMock(
                project_path=dev_path,
                link_type=constants.GITLINK_TYPE_GIT,
            )
            config.skip_git_update = lambda: False

            materialized = self.materializer.materialize_for_odpm_json(config)

            config.developing_project.build_project.assert_not_called()
            self.assertFalse(materialized)
            self.assertFalse(self.materializer.developing_repo_materialized)

    def test_materialize_for_odpm_json_skips_file_link(self):
        config = Config.__new__(Config)
        config._user = UserSettingsState()
        config._project = ProjectSettingsState()
        config._docker = DockerLayoutState()
        config.project_dir = "/tmp/project"
        config.arguments = OdpmCliArgs(no_git_update=False)
        config.developing_project = MagicMock(
            project_path="/tmp/local_dev",
            link_type=constants.GITLINK_TYPE_FILE,
        )
        config.skip_git_update = lambda: False

        materialized = self.materializer.materialize_for_odpm_json(config)

        config.developing_project.build_project.assert_not_called()
        self.assertFalse(materialized)

    def test_materialize_for_odpm_json_skips_no_git_update(self):
        config = Config.__new__(Config)
        config._user = UserSettingsState()
        config._project = ProjectSettingsState()
        config._docker = DockerLayoutState()
        config.project_dir = "/tmp/project"
        config.arguments = OdpmCliArgs(no_git_update=True)
        config.developing_project = MagicMock(
            project_path="/tmp/missing_repo",
            link_type=constants.GITLINK_TYPE_HTTP,
        )
        config.skip_git_update = lambda: True

        materialized = self.materializer.materialize_for_odpm_json(config)

        config.developing_project.build_project.assert_not_called()
        self.assertFalse(materialized)

    def test_materialize_full_builds_when_not_yet_materialized(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs(branch="18.0")
        config.developing_project = MagicMock()

        self.materializer.materialize_full(config)

        config.developing_project.build_project.assert_called_once()
        config.developing_project.switch_to_branch.assert_called_once_with("18.0")
        self.assertTrue(self.materializer.developing_repo_materialized)

    def test_materialize_for_odpm_json_creates_project_symlink_when_branch_set(self):
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as clone_root:
            dev_path = os.path.join(clone_root, "digital-autoparts")
            os.makedirs(dev_path)
            Path(os.path.join(dev_path, constants.PROJECT_CONFIG_FILE_NAME)).write_text(
                '{"odpm_version": "3.0"}',
                encoding="utf-8",
            )

            config = Config.__new__(Config)
            config._user = UserSettingsState()
            config._project = ProjectSettingsState()
            config._docker = DockerLayoutState()
            config.project_dir = project_dir
            config.arguments = OdpmCliArgs(branch="17.0-dev", no_git_update=False)
            config.developing_project = MagicMock(
                project_path=dev_path,
                link_type=constants.GITLINK_TYPE_SSH,
            )
            config.developing_project.build_project = lambda: None
            config.developing_project.switch_to_branch = lambda _branch: None
            config.skip_git_update = lambda: False
            config.dependencies_dirs = []
            config.repo_odpm_json = ""

            self.materializer.materialize_for_odpm_json(config)

            link_path = os.path.join(project_dir, os.path.basename(dev_path))
            self.assertTrue(os.path.islink(link_path))
            self.assertEqual(os.path.realpath(link_path), os.path.realpath(dev_path))

    def test_materialize_full_skips_when_already_materialized(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs(branch="17.0")
        config.developing_project = MagicMock()
        self.materializer._developing_repo_materialized = True

        self.materializer.materialize_full(config)

        config.developing_project.build_project.assert_not_called()
        config.developing_project.switch_to_branch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
