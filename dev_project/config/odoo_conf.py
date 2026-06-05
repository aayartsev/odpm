from __future__ import annotations

import ast
import configparser
import os
import pathlib
from typing import TYPE_CHECKING

from .. import constants
from .types import SubProject

if TYPE_CHECKING:
    from .config import Config


class OdooConfBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config

    def check_project_for_subprojects(self, project_path: str) -> list[SubProject]:
        subprojects_data = {}
        list_of_subprojects = []
        set_of_python_packages = set()
        for root, dirs, files in os.walk(project_path):
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
        self.config.catalogs_of_modules_data = []
        self.config.docker_dirs_with_addons = []
        self.config.list_of_developing_project_subprojects_data = []

        if self.config.developing_project:
            self.config.list_of_developing_project_subprojects_data = (
                self.check_project_for_subprojects(
                    self.config.developing_project.project_path
                )
            )
            if self.config.list_of_developing_project_subprojects_data:
                self.config.catalogs_of_modules_data.extend(
                    self.config.list_of_developing_project_subprojects_data
                )
                for subproject in self.config.list_of_developing_project_subprojects_data:
                    self.config.docker_dirs_with_addons.append(
                        str(
                            pathlib.PurePosixPath(
                                self.config.docker_odoo_project_dir_path,
                                subproject.subproject_rel_path,
                            )
                        )
                    )
            else:
                self.config.docker_dirs_with_addons.append(
                    self.config.docker_odoo_project_dir_path
                )

        odoo_addons_modules_data = self.check_project_for_subprojects(
            os.path.join(self.config.odoo_src_dir, "addons")
        )
        self.config.catalogs_of_modules_data.extend(odoo_addons_modules_data)
        self.config.docker_dirs_with_addons.append(
            str(
                pathlib.PurePosixPath(
                    self.config.docker_odoo_dir, self.config.platform_name, "addons"
                )
            )
        )
        if os.path.exists(os.path.join(self.config.odoo_src_dir, "addons")):
            self.config.docker_dirs_with_addons.append(
                str(pathlib.PurePosixPath(self.config.docker_odoo_dir, "addons"))
            )

    def generate_odoo_conf_docker_data(self) -> None:
        odoo_config = configparser.ConfigParser()
        odoo_config.read(self.config.path_odoo_conf)
        if "options" not in odoo_config:
            odoo_config["options"] = {}
        odoo_config["options"]["addons_path"] = ",".join(
            self.config.docker_dirs_with_addons
        )
        odoo_config["options"]["data_dir"] = str(
            pathlib.PurePosixPath(
                self.config.docker_project_dir, ".local/share/Odoo"
            )
        )
        self.config.odoo_config_data = {
            section: dict(odoo_config.items(section))
            for section in odoo_config.sections()
        }
