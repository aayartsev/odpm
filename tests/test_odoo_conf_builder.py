import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.config.odoo_conf import (
    OdooConfBuilder,
    odoo_conf_on_disk_needs_regeneration,
)
from dev_project.config.types import SubProject


class OdooConfBuilderTests(unittest.TestCase):
    def _builder(self, config: MagicMock | None = None) -> OdooConfBuilder:
        return OdooConfBuilder(config or MagicMock())

    def test_get_manifest_data_reads_python_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest = Path(tmp_dir) / "__manifest__.py"
            manifest.write_text(
                "{'external_dependencies': {'python': ['requests', 'xlrd']}}",
                encoding="utf-8",
            )
            packages = self._builder().get_names_of_python_packages_from_manifest(
                str(manifest)
            )
            self.assertEqual(packages, ["requests", "xlrd"])

    def test_check_project_for_subprojects_groups_modules_by_parent(self):
        with tempfile.TemporaryDirectory() as project_dir:
            addon_root = Path(project_dir) / "addons_pkg"
            module_a = addon_root / "module_a"
            module_b = addon_root / "module_b"
            module_a.mkdir(parents=True)
            module_b.mkdir(parents=True)
            (module_a / "__manifest__.py").write_text("{}", encoding="utf-8")
            (module_b / "__manifest__.py").write_text("{}", encoding="utf-8")

            subprojects = self._builder().check_project_for_subprojects(project_dir)
            self.assertEqual(len(subprojects), 1)
            subproject: SubProject = subprojects[0]
            self.assertEqual(subproject.subproject_rel_path, "addons_pkg")
            self.assertEqual(len(subproject.list_of_modules), 2)

    def test_generate_odoo_conf_docker_data_writes_addons_path_and_data_dir(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text("[options]\nadmin_passwd = admin\n", encoding="utf-8")

            config = MagicMock()
            config.path_odoo_conf = str(conf_path)
            config.docker_dirs_with_addons = [
                "/home/odoo/extra-addons",
                "/home/odoo/odoo/addons",
            ]
            config.docker_project_dir = "/home/odoo"

            OdooConfBuilder(config).generate_odoo_conf_docker_data()

            self.assertEqual(
                config.odoo_config_data["options"]["addons_path"],
                "/home/odoo/extra-addons,/home/odoo/odoo/addons",
            )
            self.assertEqual(
                config.odoo_config_data["options"]["data_dir"],
                "/home/odoo/.local/share/Odoo",
            )

    def test_odoo_conf_on_disk_needs_regeneration_when_db_host_missing(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text("[options]\nadmin_passwd = admin\n", encoding="utf-8")
            self.assertTrue(odoo_conf_on_disk_needs_regeneration(str(conf_path)))

    def test_odoo_conf_on_disk_needs_regeneration_when_db_settings_present(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "\n".join(
                    [
                        "[options]",
                        "db_host = db",
                        "db_port = 5432",
                        "db_user = odoo",
                        "db_password = odoo",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertFalse(odoo_conf_on_disk_needs_regeneration(str(conf_path)))

    def test_populate_addons_paths_without_subprojects_uses_project_dir(self):
        config = MagicMock()
        config.developing_project = MagicMock(project_path="/tmp/dev/project")
        config.docker_odoo_project_dir_path = "/home/odoo/extra-addons/project"
        config.odoo_src_dir = "/tmp/odoo/src"
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.platform_name = "odoo"
        config.catalogs_of_modules_data = []
        config.docker_dirs_with_addons = []
        config.list_of_developing_project_subprojects_data = []

        builder = OdooConfBuilder(config)
        builder.check_project_for_subprojects = MagicMock(return_value=[])
        builder.populate_addons_paths()

        self.assertEqual(
            config.docker_dirs_with_addons[0],
            "/home/odoo/extra-addons/project",
        )
        self.assertIn(
            "/home/odoo/odoo/odoo/addons",
            config.docker_dirs_with_addons,
        )


if __name__ == "__main__":
    unittest.main()
