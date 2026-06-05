import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project.project_env.environment import CreateProjectEnvironment
from dev_project.project_env.links import ProjectLinks


class ProjectLinksDependencyTests(unittest.TestCase):
    def test_resolve_dependencies_skips_oca_when_no_git_update(self):
        env = MagicMock()
        env.config = MagicMock()
        env.config.dependencies = ["https://github.com/OCA/partner-contact.git"]
        env.config.use_oca_dependencies = True
        env.config.skip_git_update.return_value = True

        resolved = ProjectLinks(env)._resolve_dependencies()

        self.assertEqual(
            resolved,
            ["https://github.com/OCA/partner-contact.git"],
        )


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

            with patch("dev_project.project_env.links.os.chdir") as mock_chdir:
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


class CreateProjectEnvironmentDownloadTests(unittest.TestCase):
    @patch("dev_project.project_env.environment.subprocess.run")
    @patch("dev_project.project_env.environment.delete_files_in_directory")
    def test_download_odoo_repository_uses_cwd_not_chdir(
        self, _mock_delete, mock_run
    ):
        config = MagicMock()
        config.odoo_src_dir = "/tmp/odoo_projects/odoo"
        config.system_checker = MagicMock()
        env = CreateProjectEnvironment(config)

        with patch("dev_project.project_env.environment.os.chdir") as mock_chdir:
            env.download_odoo_repository()

        mock_chdir.assert_not_called()
        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args.kwargs.get("cwd"), "/tmp/odoo_projects")

    @patch("dev_project.project_env.environment.os.remove")
    @patch("dev_project.project_env.environment.os.replace")
    @patch("dev_project.project_env.environment.un_zip_file_to_directory")
    @patch("dev_project.project_env.environment.download_file")
    @patch("dev_project.project_env.environment.delete_files_in_directory")
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
        config.system_checker = MagicMock()
        env = CreateProjectEnvironment(config)

        with patch("dev_project.project_env.environment.os.chdir") as mock_chdir:
            env.download_odoo_nightly_build()

        mock_chdir.assert_not_called()
        mock_unzip.assert_called_once()
        self.assertEqual(mock_unzip.call_args.args[0], "/tmp/odoo_projects")


if __name__ == "__main__":
    unittest.main()
