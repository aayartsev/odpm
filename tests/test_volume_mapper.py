import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.dependency_resolver import DependencyResolutionResult
from dev_project.host.ports import BootstrapHandle
from dev_project.project_env.volume_mapper import VolumeMapper


class VolumeMapperTests(unittest.TestCase):
    def _make_env(self):
        config = MagicMock()
        config.odoo_src_dir = "/tmp/odoo"
        config.docker_layout.venv_dir = "/tmp/venv"
        config.docker_layout.odoo_tests_dir = "/tmp/tests"
        config.program_dir = "/tmp/program"
        config.docker_layout.docker_odoo_dir = "/docker/odoo"
        config.docker_layout.docker_venv_dir = "/docker/venv"
        config.docker_layout.docker_temp_tests_dir = "/docker/tests"
        config.docker_layout.docker_dev_project_dir = "/docker/dev_project"
        config.docker_layout.docker_backups_dir = "/docker/backups"
        config.docker_layout.docker_project_dir = "/docker/project"
        config.docker_layout.dir_for_odoo_container_home = "/tmp/home"
        config.developing_project = MagicMock(project_path="/tmp/developing")
        config.docker_layout.docker_odoo_project_dir_path = "/docker/developing"
        config.developing_project_dir_path = "/tmp/developing"
        config.docker_layout.docker_extra_addons = "/docker/addons"
        config.docker_layout.dependencies_projects = []
        config.docker_layout.dependencies_dirs = []
        config.docker_layout.docker_dirs_with_addons = []
        config.user_settings.pre_commit_map_files = []
        config.check_project_for_subprojects = MagicMock(return_value=[])
        user_env = MagicMock()
        user_env.backups = "/tmp/backups"
        config.user_env = user_env
        env = MagicMock()
        env.bootstrap = BootstrapHandle(_assembled=config)
        env.user_env = user_env
        env.mapped_folders = []
        host_ctx = MagicMock()
        host_ctx.project_dir = config.project_dir
        host_ctx.program_dir = config.program_dir
        host_ctx.user_settings = config.user_settings
        host_ctx.project_settings = config.project_settings
        host_ctx.docker_layout = config.docker_layout
        host_ctx.policy = getattr(config, "policy", MagicMock())
        layout = MagicMock()
        layout.catalogs_of_modules_data = []
        host_ctx.addon_layout = layout
        env.host_ctx = host_ctx
        return env

    def test_build_base_folders_includes_developing_project(self):
        env = self._make_env()
        folders = VolumeMapper(env).build_base_folders()

        self.assertEqual(len(folders), 8)
        self.assertEqual(folders[-1].local, "/tmp/developing")
        self.assertEqual(folders[-1].docker, "/docker/developing")

    def test_append_dependency_mounts_skips_materialize_when_requested(self):
        env = self._make_env()
        url = "https://github.com/acme/A.git"
        dependency = MagicMock(
            is_cloned=True,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        env.bootstrap.handle_git_link = MagicMock(return_value=dependency)
        env.bootstrap.ensure_git_repo_symlink = MagicMock()
        resolution = DependencyResolutionResult(
            urls=[url],
            nested_fragments=[],
        )

        VolumeMapper(env).append_dependency_mounts(
            resolution,
            materialize_deps=True,
            skip_materialize=True,
        )

        env.bootstrap.handle_git_link.assert_called_once_with(url, materialize=False)
        self.assertEqual(len(env.mapped_folders), 1)
        self.assertEqual(env.mapped_folders[0].local, "/tmp/dep")

    def test_append_dependency_mounts_probes_repo_when_skip_materialize(self):
        env = self._make_env()
        url = "https://github.com/acme/A.git"
        dependency = MagicMock(
            is_cloned=False,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        dependency.build_project = MagicMock(side_effect=lambda: setattr(dependency, "is_cloned", True))
        env.bootstrap.handle_git_link = MagicMock(return_value=dependency)
        env.bootstrap.ensure_git_repo_symlink = MagicMock()
        resolution = DependencyResolutionResult(
            urls=[url],
            nested_fragments=[],
        )

        VolumeMapper(env).append_dependency_mounts(
            resolution,
            materialize_deps=True,
            skip_materialize=True,
        )

        env.bootstrap.handle_git_link.assert_called_once_with(url, materialize=False)
        dependency.build_project.assert_called_once()
        self.assertEqual(len(env.mapped_folders), 1)
        self.assertEqual(env.mapped_folders[0].local, "/tmp/dep")

    def test_map_pre_commit_files_copies_and_mounts_existing_file(self):
        with tempfile.TemporaryDirectory() as project_dir:
            env = self._make_env()
            env.bootstrap._assembled.project_dir = project_dir
            env.host_ctx.project_dir = project_dir
            env.bootstrap._assembled.developing_project_dir_path = project_dir
            env.bootstrap._assembled.docker_layout.docker_odoo_project_dir_path = "/docker/developing"
            env.bootstrap._assembled.user_settings.pre_commit_map_files = [".pre-commit-config.yaml"]
            source = os.path.join(project_dir, ".pre-commit-config.yaml")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write("repos: []\n")

            VolumeMapper(env).map_pre_commit_files()

            self.assertEqual(len(env.mapped_folders), 1)
            mount = env.mapped_folders[0]
            self.assertTrue(os.path.exists(mount.local))
            self.assertEqual(
                mount.docker,
                "/docker/developing/.pre-commit-config.yaml",
            )


if __name__ == "__main__":
    unittest.main()
