from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .types import SymlinksSources

if TYPE_CHECKING:
    from ..config.config import Config


class SymlinkManager:
    def __init__(self, config: Config) -> None:
        self.config = config

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

    def _delete_old_links(self, dir_to_clean: str, current_links) -> None:
        if not os.path.isdir(dir_to_clean):
            return
        for item in os.listdir(dir_to_clean):
            link_path = os.path.join(dir_to_clean, item)
            if os.path.islink(link_path) and item not in current_links:
                os.unlink(link_path)

    def _create_new_links(self, dir_to_create: str, current_links) -> None:
        os.makedirs(dir_to_create, exist_ok=True)
        for dep_for_link in current_links:
            dep_dir_name = os.path.basename(dep_for_link)
            link_path = os.path.join(dir_to_create, dep_dir_name)
            try:
                os.symlink(dep_for_link, link_path)
                self.config.symlinks_sources.append(
                    SymlinksSources(
                        source_path=dep_for_link,
                        link_path=os.path.join(dep_for_link, link_path),
                    )
                )
            except FileExistsError:
                pass
