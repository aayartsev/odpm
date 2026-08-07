import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.config.odoo_conf import (
    OdooConfBuilder,
    odoo_conf_db_host_mismatch,
    odoo_conf_on_disk_needs_regeneration,
)
from dev_project.config.state import AddonLayoutState, BootstrapState, DockerLayoutState
from dev_project.config.types import SubProject
from dev_project.manifest.reader import ManifestView


def _config_with_layout_slices() -> MagicMock:
    config = MagicMock()
    config.docker_layout = DockerLayoutState()
    config.addon_layout = AddonLayoutState()
    return config


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

            config = _config_with_layout_slices()
            config.docker_layout.path_odoo_conf = str(conf_path)
            config.docker_layout.docker_dirs_with_addons = [
                "/home/odoo/extra-addons",
                "/home/odoo/odoo/addons",
            ]
            config.docker_layout.docker_project_dir = "/home/odoo"

            OdooConfBuilder(config).generate_odoo_conf_docker_data()

            self.assertEqual(
                config.docker_layout.odoo_config_data["options"]["addons_path"],
                "/home/odoo/extra-addons,/home/odoo/odoo/addons",
            )
            self.assertEqual(
                config.docker_layout.odoo_config_data["options"]["data_dir"],
                "/home/odoo/.local/share/Odoo",
            )

    def test_generate_odoo_conf_docker_data_applies_manifest_overrides(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "[options]\nproxy_mode = False\nlog_level = info\n",
                encoding="utf-8",
            )

            config = _config_with_layout_slices()
            config.path_odoo_conf = str(conf_path)
            config.docker_layout.path_odoo_conf = str(conf_path)
            config.docker_layout.docker_dirs_with_addons = ["/home/odoo/extra-addons"]
            config.docker_layout.docker_project_dir = "/home/odoo"
            config.bootstrap = BootstrapState(
                manifest_view=ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.5.0",
                    raw_normalized={},
                    odoo_conf={
                        "options": {
                            "proxy_mode": "True",
                            "workers": "2",
                        }
                    },
                )
            )

            OdooConfBuilder(config).generate_odoo_conf_docker_data()

            options = config.docker_layout.odoo_config_data["options"]
            self.assertEqual(options["proxy_mode"], "True")
            self.assertEqual(options["log_level"], "info")
            self.assertEqual(options["workers"], "2")
            self.assertEqual(options["addons_path"], "/home/odoo/extra-addons")
            self.assertEqual(options["data_dir"], "/home/odoo/.local/share/Odoo")

    def test_generate_odoo_conf_docker_data_applies_scenario_effective_odoo_conf(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "[options]\nproxy_mode = False\nworkers = 0\n",
                encoding="utf-8",
            )

            config = _config_with_layout_slices()
            config.path_odoo_conf = str(conf_path)
            config.docker_layout.path_odoo_conf = str(conf_path)
            config.docker_layout.docker_dirs_with_addons = ["/home/odoo/extra-addons"]
            config.docker_layout.docker_project_dir = "/home/odoo"
            config.bootstrap = BootstrapState(
                manifest_view=ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.6.0",
                    raw_normalized={},
                    odoo_conf={
                        "options": {
                            "proxy_mode": "True",
                            "workers": "4",
                        }
                    },
                )
            )

            OdooConfBuilder(config).generate_odoo_conf_docker_data()

            options = config.docker_layout.odoo_config_data["options"]
            self.assertEqual(options["proxy_mode"], "True")
            self.assertEqual(options["workers"], "4")

    def test_generate_odoo_conf_docker_data_merges_extra_sections(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "[options]\nproxy_mode = False\n"
                "[redis_server]\nhost = old\nport = 6379\n",
                encoding="utf-8",
            )

            config = _config_with_layout_slices()
            config.path_odoo_conf = str(conf_path)
            config.docker_layout.path_odoo_conf = str(conf_path)
            config.docker_layout.docker_dirs_with_addons = ["/home/odoo/extra-addons"]
            config.docker_layout.docker_project_dir = "/home/odoo"
            config.bootstrap = BootstrapState(
                manifest_view=ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.6.0",
                    raw_normalized={},
                    odoo_conf={
                        "redis_server": {
                            "host": "redis",
                            "password": "pw",
                        },
                        "s3_server": {
                            "endpoint": "minio:9000",
                            "secret_key": "msecret",
                        },
                    },
                )
            )

            OdooConfBuilder(config).generate_odoo_conf_docker_data()

            data = config.docker_layout.odoo_config_data
            self.assertEqual(data["redis_server"]["host"], "redis")
            self.assertEqual(data["redis_server"]["port"], "6379")
            self.assertEqual(data["redis_server"]["password"], "pw")
            self.assertEqual(data["s3_server"]["endpoint"], "minio:9000")
            self.assertEqual(data["s3_server"]["secret_key"], "msecret")

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

    def test_odoo_conf_on_disk_needs_regeneration_when_db_host_mismatch(self):
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
            self.assertTrue(
                odoo_conf_on_disk_needs_regeneration(
                    str(conf_path), expected_db_host="db-dev"
                )
            )

    def test_odoo_conf_db_host_mismatch(self):
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
            self.assertTrue(odoo_conf_db_host_mismatch(str(conf_path), "db-dev"))
            self.assertFalse(odoo_conf_db_host_mismatch(str(conf_path), "db"))

    def test_populate_addons_paths_without_subprojects_uses_project_dir(self):
        config = _config_with_layout_slices()
        config.developing_project = MagicMock(project_path="/tmp/dev/project")
        config.docker_odoo_project_dir_path = "/home/odoo/extra-addons/project"
        config.odoo_src_dir = "/tmp/odoo/src"
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.platform_name = "odoo"

        builder = OdooConfBuilder(config)
        builder.check_project_for_subprojects = MagicMock(return_value=[])
        builder.populate_addons_paths()

        self.assertEqual(
            config.docker_layout.docker_dirs_with_addons[0],
            "/home/odoo/extra-addons/project",
        )
        self.assertIn(
            "/home/odoo/odoo/odoo/addons",
            config.docker_layout.docker_dirs_with_addons,
        )


if __name__ == "__main__":
    unittest.main()
