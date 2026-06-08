import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.project_env.environment import CreateProjectEnvironment
from dev_project.project_env.links import ProjectLinks
from dev_project.project_env.services import PlatformSourcesService
from dev_project.dependency_resolver import DependencyResolutionResult, NestedOdpmFragment


class ProjectLinksCheckoutTests(unittest.TestCase):
    def test_checkout_project_disables_update_when_pinned(self):
        config = MagicMock()
        config.update_git_repos = True
        config.clean_git_repos = False
        config.odoo_version = "19.0"
        env = MagicMock()
        env.config = config
        project = MagicMock()
        lock_manager = MagicMock()
        lock_manager.is_pinned.return_value = True

        ProjectLinks(env).checkout_project(project, lock_manager=lock_manager)

        project.checkout_repository.assert_called_once_with(
            "19.0",
            clean_git_repos=False,
            update_git_repos=False,
        )

    def test_checkout_project_keeps_update_when_not_pinned(self):
        config = MagicMock()
        config.update_git_repos = True
        config.clean_git_repos = True
        config.odoo_version = "17.0"
        env = MagicMock()
        env.config = config
        project = MagicMock()
        lock_manager = MagicMock()
        lock_manager.is_pinned.return_value = False

        ProjectLinks(env).checkout_project(project, lock_manager=lock_manager)

        project.checkout_repository.assert_called_once_with(
            "17.0",
            clean_git_repos=True,
            update_git_repos=True,
        )


class ProjectLinksDevelopingCheckoutTests(unittest.TestCase):
    def test_checkout_dependencies_skips_developing_without_explicit_branch(self):
        config = MagicMock()
        config.odoo_version = "17.0"
        config.odoo_platform_project = MagicMock()
        config.dependencies_projects = []
        developing = MagicMock()
        developing.link_type = constants.GITLINK_TYPE_SSH
        developing.is_true = True
        developing.branch_explicit = False
        developing.commit_explicit = False
        config.developing_project = developing
        env = MagicMock()
        env.config = config
        links = ProjectLinks(env)
        links.checkout_project = MagicMock()

        links.checkout_dependencies()

        links.checkout_project.assert_called_once_with(
            config.odoo_platform_project,
            lock_manager=None,
        )

    def test_checkout_dependencies_includes_pinned_developing(self):
        config = MagicMock()
        config.odoo_version = "17.0"
        config.odoo_platform_project = MagicMock()
        config.dependencies_projects = []
        developing = MagicMock()
        developing.link_type = constants.GITLINK_TYPE_SSH
        developing.is_true = True
        developing.branch_explicit = False
        developing.commit_explicit = False
        config.developing_project = developing
        env = MagicMock()
        env.config = config
        links = ProjectLinks(env)
        links.checkout_project = MagicMock()
        lock_manager = MagicMock()
        lock_manager.is_pinned.side_effect = (
            lambda project: project is developing
        )

        links.checkout_dependencies(lock_manager=lock_manager)

        self.assertEqual(links.checkout_project.call_count, 2)
        links.checkout_project.assert_any_call(
            developing,
            lock_manager=lock_manager,
        )


class ProjectLinksDependencyTests(unittest.TestCase):
    def test_resolve_dependencies_skips_oca_when_no_git_update(self):
        env = MagicMock()
        env.config = MagicMock()
        env.config.dependencies = ["https://github.com/OCA/partner-contact.git"]
        env.config.use_oca_dependencies = True
        env.config.skip_git_update.return_value = True

        resolved = ProjectLinks(env)._resolve_dependencies()

        self.assertEqual(
            resolved.urls,
            ["https://github.com/OCA/partner-contact.git"],
        )
        self.assertEqual(resolved.transitive_requirements, [])
        self.assertEqual(resolved.nested_fragments, [])


class ProjectLinksNestedOdpmDiscoveryTests(unittest.TestCase):
    def _make_links(self, config):
        env = MagicMock()
        env.config = config
        links = ProjectLinks(env)
        links.checkout_project = MagicMock()
        return links

    def test_discover_dependency_extensions_reads_nested_odpm_json(self):
        with tempfile.TemporaryDirectory() as base:
            dep_a = Path(base) / "dep_a"
            dep_b = Path(base) / "dep_b"
            dep_a.mkdir()
            dep_b.mkdir()
            (dep_a / "odpm.json").write_text(
                json.dumps(
                    {
                        "dependencies": ["https://github.com/acme/B.git"],
                        "requirements_txt": ["openupgradelib"],
                        "odoo_version": "17.0",
                    }
                ),
                encoding="utf-8",
            )

            url_a = "https://github.com/acme/A.git"
            url_b = "https://github.com/acme/B.git"

            def handle_git_link(dependency_string, materialize=False):
                link = MagicMock()
                link.is_cloned = dependency_string in (url_a, url_b)
                if dependency_string == url_a:
                    link.project_path = str(dep_a)
                elif dependency_string == url_b:
                    link.project_path = str(dep_b)
                else:
                    link.project_path = ""
                return link

            config = MagicMock()
            config.dependencies = [url_a]
            config.use_oca_dependencies = True
            config.skip_git_update.return_value = False
            config.developing_project = MagicMock(project_path="")
            config.handle_git_link = MagicMock(side_effect=handle_git_link)

            result = self._make_links(config)._resolve_dependencies()

            self.assertEqual(result.urls, [url_a, url_b])
            self.assertEqual(result.transitive_requirements, ["openupgradelib"])
            self.assertEqual(len(result.nested_fragments), 1)
            config.handle_git_link.assert_any_call(url_a, materialize=True)

    def test_discover_dependency_extensions_merges_oca_and_nested_urls(self):
        with tempfile.TemporaryDirectory() as base:
            dep_a = Path(base) / "dep_a"
            dep_a.mkdir()
            (dep_a / "oca_dependencies.txt").write_text(
                "https://github.com/OCA/B.git\n",
                encoding="utf-8",
            )
            (dep_a / "odpm.json").write_text(
                json.dumps(
                    {
                        "dependencies": ["https://github.com/acme/C.git"],
                        "requirements_txt": ["requests"],
                    }
                ),
                encoding="utf-8",
            )

            url_a = "https://github.com/acme/A.git"
            url_b = "https://github.com/OCA/B.git"
            url_c = "https://github.com/acme/C.git"

            def handle_git_link(dependency_string, materialize=False):
                link = MagicMock()
                link.is_cloned = dependency_string == url_a
                link.project_path = str(dep_a) if dependency_string == url_a else ""
                return link

            config = MagicMock()
            config.dependencies = [url_a]
            config.use_oca_dependencies = True
            config.skip_git_update.return_value = False
            config.developing_project = MagicMock(project_path="")
            config.handle_git_link = MagicMock(side_effect=handle_git_link)

            result = self._make_links(config)._resolve_dependencies()

            self.assertEqual(result.urls, [url_a, url_b, url_c])
            self.assertEqual(result.transitive_requirements, ["requests"])

    def test_discover_dependency_extensions_skips_materialize_when_no_git_update(self):
        config = MagicMock()
        config.dependencies = ["https://github.com/acme/A.git"]
        config.use_oca_dependencies = True
        config.skip_git_update.return_value = True
        links = self._make_links(config)

        result = links._resolve_dependencies()

        self.assertEqual(result.urls, config.dependencies)
        config.handle_git_link.assert_not_called()

    def test_map_folders_skips_rematerialize_when_discovery_enabled(self):
        url = "https://github.com/acme/A.git"
        config = MagicMock()
        config.use_oca_dependencies = True
        config.skip_git_update.return_value = False
        config.developing_project = MagicMock(project_path="")
        config.pre_commit_map_files = []
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
        config.docker_odoo_project_dir_path = "/docker/project"
        config.developing_project_dir_path = "/tmp/developing"
        config.docker_extra_addons = "/docker/addons"
        config.dependencies_projects = []
        config.dependencies_dirs = []
        config.catalogs_of_modules_data = []
        config.docker_dirs_with_addons = []
        config.check_project_for_subprojects = MagicMock(return_value=[])
        dependency = MagicMock(
            is_cloned=True,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        config.handle_git_link = MagicMock(return_value=dependency)
        env = MagicMock()
        env.config = config
        env.mapped_folders = []
        links = ProjectLinks(env)
        links._resolve_dependencies = MagicMock(
            return_value=DependencyResolutionResult(
                urls=[url],
                transitive_requirements=[],
                nested_fragments=[],
            )
        )

        links.map_folders()

        config.handle_git_link.assert_called_once_with(url, materialize=False)

    def test_map_folders_applies_transitive_requirements_from_resolution(self):
        url = "https://github.com/acme/A.git"
        fragment = NestedOdpmFragment(
            dependencies=[],
            requirements_txt=["openupgradelib"],
            odoo_version="17.0",
            python_version="3.12",
            source_path="/tmp/framework/odpm.json",
        )
        config = MagicMock()
        config.use_oca_dependencies = True
        config.skip_git_update.return_value = False
        config.developing_project = MagicMock(project_path="")
        config.pre_commit_map_files = []
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
        config.docker_odoo_project_dir_path = "/docker/project"
        config.developing_project_dir_path = "/tmp/developing"
        config.docker_extra_addons = "/docker/addons"
        config.dependencies_projects = []
        config.dependencies_dirs = []
        config.catalogs_of_modules_data = []
        config.docker_dirs_with_addons = []
        config.check_project_for_subprojects = MagicMock(return_value=[])
        config.apply_transitive_requirements = MagicMock()
        dependency = MagicMock(
            is_cloned=True,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        config.handle_git_link = MagicMock(return_value=dependency)
        env = MagicMock()
        env.config = config
        env.mapped_folders = []
        links = ProjectLinks(env)
        links._resolve_dependencies = MagicMock(
            return_value=DependencyResolutionResult(
                urls=[url],
                transitive_requirements=["openupgradelib"],
                nested_fragments=[fragment],
            )
        )

        links.map_folders()

        config.apply_transitive_requirements.assert_called_once_with(
            ["openupgradelib"],
            nested_fragments=[fragment],
        )

    def test_map_folders_skips_apply_when_resolution_has_no_transitive_data(self):
        url = "https://github.com/acme/A.git"
        config = MagicMock()
        config.use_oca_dependencies = False
        config.skip_git_update.return_value = False
        config.developing_project = MagicMock(project_path="")
        config.pre_commit_map_files = []
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
        config.docker_odoo_project_dir_path = "/docker/project"
        config.developing_project_dir_path = "/tmp/developing"
        config.docker_extra_addons = "/docker/addons"
        config.dependencies_projects = []
        config.dependencies_dirs = []
        config.catalogs_of_modules_data = []
        config.docker_dirs_with_addons = []
        config.check_project_for_subprojects = MagicMock(return_value=[])
        config.apply_transitive_requirements = MagicMock()
        dependency = MagicMock(
            is_cloned=True,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        config.handle_git_link = MagicMock(return_value=dependency)
        env = MagicMock()
        env.config = config
        env.mapped_folders = []
        links = ProjectLinks(env)
        links._resolve_dependencies = MagicMock(
            return_value=DependencyResolutionResult(
                urls=[url],
                transitive_requirements=[],
                nested_fragments=[],
            )
        )

        links.map_folders()

        config.apply_transitive_requirements.assert_not_called()


class ProjectLinksUpdateTests(unittest.TestCase):
    def test_update_links_does_not_chdir(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.dependencies_dirs = []
            config.list_for_symlinks = []
            config.catalogs_of_modules_data = []
            config.create_module_links = False
            config.symlinks_sources = []
            config.odoo_src_dir = os.path.join(project_dir, "odoo")
            config.platform_name = "odoo"
            env = MagicMock()
            env.config = config

            with patch("dev_project.project_env.symlink_manager.os.chdir") as mock_chdir:
                ProjectLinks(env).update_links()

            mock_chdir.assert_not_called()

    def test_update_links_creates_symlink_with_absolute_paths(self):
        with tempfile.TemporaryDirectory() as project_dir:
            target_dir = os.path.join(project_dir, "sources", "odoo_src")
            os.makedirs(target_dir)

            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.dependencies_dirs = []
            config.list_for_symlinks = [target_dir]
            config.catalogs_of_modules_data = []
            config.create_module_links = False
            config.symlinks_sources = []
            config.odoo_src_dir = os.path.join(project_dir, "odoo")
            config.platform_name = "odoo"
            env = MagicMock()
            env.config = config

            ProjectLinks(env).update_links()

            link_path = os.path.join(project_dir, os.path.basename(target_dir))
            self.assertTrue(os.path.islink(link_path))
            self.assertEqual(os.readlink(link_path), target_dir)

    def test_update_links_removes_stale_symlink(self):
        with tempfile.TemporaryDirectory() as project_dir:
            stale_link = os.path.join(project_dir, "stale")
            os.symlink("/tmp/old-target", stale_link)

            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.dependencies_dirs = []
            config.list_for_symlinks = []
            config.catalogs_of_modules_data = []
            config.create_module_links = False
            config.symlinks_sources = []
            config.odoo_src_dir = os.path.join(project_dir, "odoo")
            config.platform_name = "odoo"
            env = MagicMock()
            env.config = config

            ProjectLinks(env).update_links()

            self.assertFalse(os.path.lexists(stale_link))


class PlatformSourcesServiceTests(unittest.TestCase):
    @patch("dev_project.project_env.services.platform_sources.os.remove")
    @patch("dev_project.project_env.services.platform_sources.os.replace")
    @patch(
        "dev_project.project_env.services.platform_sources.un_zip_file_to_directory"
    )
    @patch("dev_project.project_env.services.platform_sources.download_file")
    @patch(
        "dev_project.project_env.services.platform_sources.delete_files_in_directory"
    )
    def test_download_odoo_nightly_build_uses_parent_dir_not_chdir(
        self,
        _mock_delete,
        _mock_download,
        mock_unzip,
        _mock_replace,
        _mock_remove,
    ):
        config = MagicMock()
        config.odoo_src_dir = "/tmp/odoo_projects/odoo"
        config.odoo_version = "17.0"
        config.odoo_build_date = "20240101"
        checker = MagicMock()
        env = CreateProjectEnvironment(config, system_checker=checker)

        with patch(
            "dev_project.project_env.services.platform_sources.os.chdir"
        ) as mock_chdir:
            PlatformSourcesService(env).download_odoo_nightly_build()

        mock_chdir.assert_not_called()
        mock_unzip.assert_called_once()
        self.assertEqual(mock_unzip.call_args.args[0], "/tmp/odoo_projects")
        checker.check_free_space_for_odoo_developing.assert_called_once_with(
            free_space_size=2.0
        )


if __name__ == "__main__":
    unittest.main()
