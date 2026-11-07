from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from ..logging import get_module_logger
from .types import SymlinksSources

if TYPE_CHECKING:
    from ..host.context import HostProjectContext
    from ..host.ports import BootstrapHandle

_logger = get_module_logger(__name__)


class SymlinkManager:
    def __init__(
        self,
        bootstrap: BootstrapHandle,
        *,
        host_ctx: HostProjectContext,
    ) -> None:
        self.bootstrap = bootstrap
        self.host_ctx = host_ctx

    def _dependencies_link_dir(self) -> str:
        layout = self.host_ctx.docker_layout
        if layout.dependencies_dir:
            return layout.dependencies_dir
        if self.host_ctx.project_dir:
            return os.path.join(self.host_ctx.project_dir, constants.DEPENDENCIES_DIR)
        return ""

    def _service_sources_link_dir(self) -> str:
        layout = self.host_ctx.docker_layout
        if layout.service_sources_dir:
            return layout.service_sources_dir
        if self.host_ctx.project_dir:
            return os.path.join(self.host_ctx.project_dir, constants.SERVICE_SOURCES_DIR)
        return ""

    def ensure_link(
        self,
        link_dir: str,
        target_path: str,
        *,
        link_name: str | None = None,
    ) -> None:
        if not link_dir or not target_path:
            return
        name = link_name or os.path.basename(target_path.rstrip(os.sep))
        if not name:
            return
        os.makedirs(link_dir, exist_ok=True)
        link_path = os.path.join(link_dir, name)
        if os.path.islink(link_path):
            if os.readlink(link_path) == target_path:
                self._record_symlink(target_path, link_path)
                return
            os.unlink(link_path)
        elif os.path.exists(link_path):
            # Do not clobber a real file/directory that occupies the link name.
            _logger.warning(
                "Skip symlink %s → %s: path exists and is not a symlink",
                link_path,
                target_path,
            )
            return
        os.symlink(target_path, link_path)
        self._record_symlink(target_path, link_path)

    def ensure_project_repo_link(self, target_path: str) -> None:
        if not self.host_ctx.project_dir:
            return
        self.ensure_link(self.host_ctx.project_dir, target_path)

    def ensure_dependency_repo_link(self, target_path: str) -> None:
        link_dir = self._dependencies_link_dir()
        if not link_dir:
            return
        self.ensure_link(link_dir, target_path)

    def sync_service_source_project_links(self, source_paths: dict[str, str]) -> None:
        link_dir = self._service_sources_link_dir()
        if not link_dir:
            return
        if source_paths:
            os.makedirs(link_dir, exist_ok=True)
            for name, target in source_paths.items():
                if not name or not target:
                    continue
                link_path = os.path.join(link_dir, name)
                if os.path.islink(link_path):
                    if os.readlink(link_path) == target:
                        self._record_symlink(target, link_path)
                        continue
                    os.unlink(link_path)
                elif os.path.exists(link_path):
                    continue
                self.ensure_link(link_dir, target, link_name=name)
        if not os.path.isdir(link_dir):
            return
        expected = set(source_paths)
        for item in os.listdir(link_dir):
            link_path = os.path.join(link_dir, item)
            if os.path.islink(link_path) and item not in expected:
                os.unlink(link_path)

    def update_links(self) -> None:
        layout = self.host_ctx.docker_layout
        if not os.path.exists(layout.dependencies_dir) and layout.dependencies_dirs:
            os.mkdir(layout.dependencies_dir)
        self._delete_old_links(
            self.host_ctx.project_dir,
            layout.list_for_symlinks,
        )
        self._create_new_links(
            self.host_ctx.project_dir,
            layout.list_for_symlinks,
        )
        if layout.dependencies_dirs:
            self._delete_old_links(
                layout.dependencies_dir,
                layout.dependencies_dirs,
            )
            self._create_new_links(
                layout.dependencies_dir,
                layout.dependencies_dirs,
            )
        list_of_all_modules = []
        for catalog_of_modules in self.host_ctx.addon_layout.catalogs_of_modules_data:
            list_of_all_modules.extend(catalog_of_modules.list_of_modules)

        if list_of_all_modules:
            odoo_src_addons_dir = os.path.join(
                self.bootstrap.odoo_src_dir,
                self.host_ctx.project_settings.platform_name,
                "addons",
            )
            self._delete_old_links(odoo_src_addons_dir, list_of_all_modules)
            if self.host_ctx.user_settings.create_module_links:
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
        layout = self.host_ctx.docker_layout
        for entry in layout.symlinks_sources:
            if entry.link_path == link_path:
                return
        layout.symlinks_sources.append(
            SymlinksSources(
                source_path=source_path,
                link_path=link_path,
            )
        )
