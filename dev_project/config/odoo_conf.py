from __future__ import annotations

import ast
import configparser
import os
import pathlib
from typing import TYPE_CHECKING

from .. import constants
from ..manifest.odoo_conf import merge_odoo_conf_sections, odoo_conf_from_manifest
from .types import SubProject

if TYPE_CHECKING:
    from .config import Config

_REQUIRED_DB_OPTION_KEYS = ("db_host", "db_port", "db_user", "db_password")
_UNRESOLVED_DB_MARKERS = (
    constants.POSTGRES_ODOO_HOST_MARKER,
    constants.POSTGRES_ODOO_USER_MARKER,
    constants.POSTGRES_ODOO_PASS_MARKER,
    constants.POSTGRES_ODOO_PORT_MARKER,
)


def odoo_conf_db_host_mismatch(path: str, expected_host: str) -> bool:
    if not expected_host or not isinstance(path, str) or not path or not os.path.isfile(path):
        return False
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except OSError:
        return False
    if "options" not in parser:
        return False
    db_host = (parser["options"].get("db_host") or "").strip()
    if not db_host:
        return False
    return db_host != expected_host


def odoo_conf_on_disk_needs_regeneration(
    path: str, *, expected_db_host: str | None = None
) -> bool:
    if not isinstance(path, str) or not path or not os.path.isfile(path):
        return True
    try:
        with open(path, encoding="utf-8") as reader:
            content = reader.read()
    except OSError:
        return True
    if any(marker in content for marker in _UNRESOLVED_DB_MARKERS):
        return True
    parser = configparser.ConfigParser()
    parser.read(path)
    if "options" not in parser:
        return True
    options = parser["options"]
    if any(not options.get(key) for key in _REQUIRED_DB_OPTION_KEYS):
        return True
    if expected_db_host and odoo_conf_db_host_mismatch(path, expected_db_host):
        return True
    return False


class OdooConfBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config

    def check_project_for_subprojects(self, project_path: str) -> list[SubProject]:
        subprojects_data = {}
        list_of_subprojects = []
        set_of_python_packages = set()
        for root, _dirs, files in os.walk(project_path):
            for file in files:
                if file in constants.MODULE_FILES:
                    subproject_dir_path = os.path.abspath(os.path.join(root, os.pardir))
                    if not subprojects_data.get(subproject_dir_path, False):
                        subprojects_data[subproject_dir_path] = [root]
                    else:
                        subprojects_data[subproject_dir_path].append(root)
                    list_of_python_packages_for_module = (
                        self.get_names_of_python_packages_from_manifest(
                            os.path.abspath(os.path.join(root, file))
                        )
                    )
                    for module in list_of_python_packages_for_module:
                        set_of_python_packages.add(module)
        for subproject_dir, module_list in subprojects_data.items():
            rel_path = os.path.relpath(subproject_dir, project_path)
            subproject = SubProject(
                subproject_dir_path=subproject_dir,
                subproject_rel_path=rel_path,
                list_of_modules=module_list,
                list_of_python_packages=list(set_of_python_packages),
            )
            list_of_subprojects.append(subproject)
        return list_of_subprojects

    def get_names_of_python_packages_from_manifest(
        self, path_to_manifest: str
    ) -> list[str]:
        manifest_data = self.get_manifest_data(path_to_manifest)
        return manifest_data.get("external_dependencies", {}).get("python", [])

    def get_manifest_data(self, path_to_manifest: str) -> dict:
        manifest_data = {}
        with open(path_to_manifest, mode="rb") as f:
            manifest_data.update(ast.literal_eval(f.read().decode("utf-8")))
        return manifest_data

    def populate_addons_paths(self) -> None:
        layout = self.config.addon_layout
        docker = self.config.docker_layout
        layout.catalogs_of_modules_data = []
        docker.docker_dirs_with_addons = []
        layout.list_of_developing_project_subprojects_data = []

        if self.config.developing_project:
            layout.list_of_developing_project_subprojects_data = (
                self.check_project_for_subprojects(
                    self.config.developing_project.project_path
                )
            )
            if layout.list_of_developing_project_subprojects_data:
                layout.catalogs_of_modules_data.extend(
                    layout.list_of_developing_project_subprojects_data
                )
                for subproject in layout.list_of_developing_project_subprojects_data:
                    docker.docker_dirs_with_addons.append(
                        str(
                            pathlib.PurePosixPath(
                                self.config.docker_odoo_project_dir_path,
                                subproject.subproject_rel_path,
                            )
                        )
                    )
            else:
                docker.docker_dirs_with_addons.append(
                    self.config.docker_odoo_project_dir_path
                )

        odoo_addons_modules_data = self.check_project_for_subprojects(
            os.path.join(self.config.odoo_src_dir, "addons")
        )
        layout.catalogs_of_modules_data.extend(odoo_addons_modules_data)
        docker.docker_dirs_with_addons.append(
            str(
                pathlib.PurePosixPath(
                    self.config.docker_odoo_dir, self.config.platform_name, "addons"
                )
            )
        )
        if os.path.exists(os.path.join(self.config.odoo_src_dir, "addons")):
            docker.docker_dirs_with_addons.append(
                str(pathlib.PurePosixPath(self.config.docker_odoo_dir, "addons"))
            )

    def generate_odoo_conf_docker_data(self) -> None:
        odoo_config = configparser.ConfigParser()
        odoo_config.read(self.config.path_odoo_conf)
        if "options" not in odoo_config:
            odoo_config["options"] = {}

        disk_data = {
            section: dict(odoo_config.items(section))
            for section in odoo_config.sections()
        }
        manifest_overrides = odoo_conf_from_manifest(
            self.config.bootstrap.manifest_view
        )
        merged = merge_odoo_conf_sections(disk_data, manifest_overrides)

        odoo_config.clear()
        for section_name, section_values in merged.items():
            odoo_config[section_name] = {}
            for key, value in section_values.items():
                odoo_config[section_name][key] = value
        if "options" not in odoo_config:
            odoo_config["options"] = {}

        odoo_config["options"]["addons_path"] = ",".join(
            self.config.docker_layout.docker_dirs_with_addons
        )
        odoo_config["options"]["data_dir"] = str(
            pathlib.PurePosixPath(
                self.config.docker_layout.docker_project_dir, ".local/share/Odoo"
            )
        )
        self.config.docker_layout.odoo_config_data = {
            section: dict(odoo_config.items(section))
            for section in odoo_config.sections()
        }
