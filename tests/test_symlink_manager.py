import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project.project_env.symlink_manager import SymlinkManager


class SymlinkManagerTests(unittest.TestCase):
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

            with patch("dev_project.project_env.symlink_manager.os.chdir") as mock_chdir:
                SymlinkManager(config).update_links()

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

            SymlinkManager(config).update_links()

            link_path = os.path.join(project_dir, os.path.basename(target_dir))
            self.assertTrue(os.path.islink(link_path))
            self.assertEqual(os.readlink(link_path), target_dir)


if __name__ == "__main__":
    unittest.main()
