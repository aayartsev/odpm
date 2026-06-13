from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from .types import SymlinksSources

if TYPE_CHECKING:
    from ..config.config import Config


class SymlinkManager:
    def __init__(self, config: Config) -> None:
        self.config = config

    def _dependencies_link_dir(self) -> str:
        if self.config.dependencies_dir:
            return self.config.dependencies_dir
        if self.config.project_dir:
            return os.path.join(self.config.project_dir, constants.DEPENDENCIES_DIR)
        return ""

    def ensure_link(self, link_dir: str, target_path: str) -> None:
        if not link_dir or not target_path:
            return
        link_name = os.path.basename(target_path.rstrip(os.sep))
        if not link_name:
            return
        os.makedirs(link_dir, exist_ok=True)
        link_path = os.path.join(link_dir, link_name)
        try:
            os.symlink(target_path, link_path)
            self._record_symlink(target_path, link_path)
        except FileExistsError:
            pass

    def ensure_project_repo_link(self, target_path: str) -> None:
        if not self.config.project_dir:
            return
        self.ensure_link(self.config.project_dir, target_path)

    def ensure_dependency_repo_link(self, target_path: str) -> None:
        link_dir = self._dependencies_link_dir()
        if not link_dir:
            return
        self.ensure_link(link_dir, target_path)

    def update_links(self) -> None:
        if (
            not os.path.exists(self.config.dependencies_dir)
            and self.config.dependencies_dirs
        ):
            os.mkdir(self.config.dependencies_dir)
        self._delete_old_links(self.config.project_dir, self.config.list_for_symlinks)
        self._create_new_links(self.config.project_dir, self.config.list_for_symlinks)
        if self.config.dependencies_dirs:
            self._delete_old_links(
                self.config.dependencies_dir, self.config.dependencies_dirs
            )
            self._create_new_links(
                self.config.dependencies_dir, self.config.dependencies_dirs
            )
        list_of_all_modules = []
        for catalog_of_modules in self.config.catalogs_of_modules_data:
            list_of_all_modules.extend(catalog_of_modules.list_of_modules)

        if list_of_all_modules:
            odoo_src_addons_dir = os.path.join(
                self.config.odoo_src_dir, self.config.platform_name, "addons"
            )
            self._delete_old_links(odoo_src_addons_dir, list_of_all_modules)
            if self.config.create_module_links:
                self._create_new_links(odoo_src_addons_dir, list_of_all_modules)

    @staticmethod
    def _link_names(current_links) -> set[str]:
        return {os.path.basename(path) for path in current_links}

    def _delete_old_links(self, dir_to_clean: str, current_links) -> None:
        if not os.path.isdir(dir_to_clean):
            return
        expected_names = self._link_names(current_links)
        for item in os.listdir(dir_to_clean):
            link_path = os.path.join(dir_to_clean, item)
            if os.path.islink(link_path) and item not in expected_names:
                os.unlink(link_path)

    def _create_new_links(self, dir_to_create: str, current_links) -> None:
        for dep_for_link in current_links:
            self.ensure_link(dir_to_create, dep_for_link)

    def _record_symlink(self, source_path: str, link_path: str) -> None:
        for entry in self.config.symlinks_sources:
            if entry.link_path == link_path:
                return
        self.config.symlinks_sources.append(
            SymlinksSources(
                source_path=source_path,
                link_path=link_path,
            )
        )
