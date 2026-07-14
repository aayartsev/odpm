"""Regression: service_sources paths must not enter addons_path."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project.git.service_sources import SERVICE_SOURCES_DIR


class ServiceSourcesAddonsPathTests(unittest.TestCase):
    def test_service_sources_dir_not_appended_to_docker_dirs_with_addons(self):
        with tempfile.TemporaryDirectory() as tmp:
            service_path = os.path.join(tmp, "odoo_projects", SERVICE_SOURCES_DIR, "autoparts_env")
            os.makedirs(service_path, exist_ok=True)

            from dev_project.config.odoo_conf import OdooConfBuilder

            config = MagicMock()
            config.dependencies_projects = []
            config.developing_project = MagicMock(project_path=os.path.join(tmp, "developing"))
            config.odoo_src_dir = os.path.join(tmp, "platform")
            config.docker_layout.docker_dirs_with_addons = []
            config.docker_layout.dependencies_dirs = []
            config.addon_layout.catalogs_of_modules_data = []
            config.addon_layout.list_of_developing_project_subprojects_data = []
            config.user_env.odoo_projects_dir = os.path.join(tmp, "odoo_projects")
            config.bootstrap.service_source_paths = {
                "autoparts_env": service_path,
            }

            builder = OdooConfBuilder(config)
            with patch.object(builder, "check_project_for_subprojects", return_value=[]):
                builder.populate_addons_paths()

            addon_paths = config.docker_layout.docker_dirs_with_addons
            for path in addon_paths:
                self.assertNotIn(SERVICE_SOURCES_DIR, path)


if __name__ == "__main__":
    unittest.main()
