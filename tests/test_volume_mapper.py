import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.dependency_resolver import DependencyResolutionResult
from dev_project.project_env.types import MappedPath
from dev_project.project_env.volume_mapper import VolumeMapper


class VolumeMapperTests(unittest.TestCase):
    def _make_env(self):
        config = MagicMock()
        config.odoo_src_dir = "/tmp/odoo"
        config.venv_dir = "/tmp/venv"
        config.odoo_tests_dir = "/tmp/tests"
        config.program_dir = "/tmp/program"
        config.docker_odoo_dir = "/docker/odoo"
        config.docker_venv_dir = "/docker/venv"
        config.docker_temp_tests_dir = "/docker/tests"
        config.docker_dev_project_dir = "/docker/dev_project"
        config.docker_backups_dir = "/docker/backups"
        config.docker_project_dir = "/docker/project"
        config.dir_for_odoo_container_home = "/tmp/home"
        config.developing_project = MagicMock(project_path="/tmp/developing")
        config.docker_odoo_project_dir_path = "/docker/developing"
        config.developing_project_dir_path = "/tmp/developing"
        config.docker_extra_addons = "/docker/addons"
        config.dependencies_projects = []
        config.dependencies_dirs = []
        config.docker_dirs_with_addons = []
        config.pre_commit_map_files = []
        config.check_project_for_subprojects = MagicMock(return_value=[])
        config.python_version = "3.12"
        config.policy = MagicMock()
        config.policy.mount_runtime_config_from_host.return_value = False
        user_env = MagicMock()
        user_env.backups = "/tmp/backups"
        config.user_env = user_env
        env = MagicMock()
        env.config = config
        env.user_env = user_env
        env.mapped_folders = []
        layout = MagicMock()
        layout.catalogs_of_modules_data = []
        env.host_ctx = MagicMock()
        env.host_ctx.addon_layout = layout
        return env

    def test_build_base_folders_includes_developing_project(self):
        env = self._make_env()
        folders = VolumeMapper(env).build_base_folders()

        self.assertEqual(len(folders), 8)
        self.assertEqual(folders[-1].local, "/tmp/developing")
        self.assertEqual(folders[-1].docker, "/docker/developing")

    def test_build_base_folders_adds_wheel_cache_when_host_mount_policy(self):
        env = self._make_env()
        env.config.policy.mount_runtime_config_from_host.return_value = True
        env.user_env.project_dotenv_dict = MagicMock(
            return_value={constants.ODPM_WHEEL_CACHE_ROOT_ENV: "/var/cache/odpm"}
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "dev_project.project_env.volume_mapper.host_cache_mounts",
                return_value=[
                    MappedPath(local=f"{tmp}/uv", docker="/cache/odpm/uv"),
                    MappedPath(
                        local=f"{tmp}/wheels/3.12",
                        docker="/cache/odpm/wheels/3.12",
                    ),
                ],
            ) as mock_mounts:
                with patch(
                    "dev_project.project_env.volume_mapper.host_golden_mounts",
                    return_value=[
                        MappedPath(
                            local=f"{tmp}/venvs",
                            docker=constants.GOLDEN_VENV_CONTAINER_ROOT,
                        )
                    ],
                ) as mock_golden:
                    folders = VolumeMapper(env).build_base_folders()
            mock_mounts.assert_called_once()
            self.assertEqual(
                mock_mounts.call_args.kwargs["python_version"], "3.12"
            )
            self.assertEqual(
                mock_mounts.call_args.kwargs["env"][constants.ODPM_WHEEL_CACHE_ROOT_ENV],
                "/var/cache/odpm",
            )
            mock_golden.assert_called_once()
            self.assertEqual(
                mock_golden.call_args.kwargs["env"][constants.ODPM_WHEEL_CACHE_ROOT_ENV],
                "/var/cache/odpm",
            )
        docker_paths = {folder.docker for folder in folders}
        self.assertIn("/cache/odpm/uv", docker_paths)
        self.assertIn("/cache/odpm/wheels/3.12", docker_paths)
        self.assertIn(constants.GOLDEN_VENV_CONTAINER_ROOT, docker_paths)

    def test_build_base_folders_skips_wheel_cache_without_host_mount_policy(self):
        env = self._make_env()
        env.config.policy.mount_runtime_config_from_host.return_value = False
        folders = VolumeMapper(env).build_base_folders()
        docker_paths = {folder.docker for folder in folders}
        self.assertNotIn("/cache/odpm/uv", docker_paths)

    def test_append_dependency_mounts_skips_materialize_when_requested(self):
        env = self._make_env()
        url = "https://github.com/acme/A.git"
        dependency = MagicMock(
            is_cloned=True,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        env.config.handle_git_link = MagicMock(return_value=dependency)
        resolution = DependencyResolutionResult(
            urls=[url],
            transitive_requirements=[],
            nested_fragments=[],
        )

        VolumeMapper(env).append_dependency_mounts(
            resolution,
            materialize_deps=True,
            skip_materialize=True,
        )

        env.config.handle_git_link.assert_called_once_with(url, materialize=False)
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
        env.config.handle_git_link = MagicMock(return_value=dependency)
        resolution = DependencyResolutionResult(
            urls=[url],
            transitive_requirements=[],
            nested_fragments=[],
        )

        VolumeMapper(env).append_dependency_mounts(
            resolution,
            materialize_deps=True,
            skip_materialize=True,
        )

        env.config.handle_git_link.assert_called_once_with(url, materialize=False)
        dependency.build_project.assert_called_once()
        self.assertEqual(len(env.mapped_folders), 1)
        self.assertEqual(env.mapped_folders[0].local, "/tmp/dep")

    def test_map_pre_commit_files_copies_and_mounts_existing_file(self):
        with tempfile.TemporaryDirectory() as project_dir:
            env = self._make_env()
            env.config.project_dir = project_dir
            env.config.developing_project_dir_path = project_dir
            env.config.docker_odoo_project_dir_path = "/docker/developing"
            env.config.pre_commit_map_files = [".pre-commit-config.yaml"]
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
