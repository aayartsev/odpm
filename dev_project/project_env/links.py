from __future__ import annotations

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from .. import constants, translations
from ..dependency_resolver import (
    DependencyDiscovery,
    DependencyResolutionResult,
    read_nested_odpm_fragment,
    read_oca_dependency_urls,
    resolve_dependencies,
)
from ..git import HandleOdooProjectLink
from ..git.deps_lock import is_remote_git_link
from ..inside_docker_app.logger import get_module_logger
from .types import MappedPath, SymlinksSources

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)


class ProjectLinks:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env
        self._dependency_resolution: DependencyResolutionResult | None = None

    @property
    def config(self):
        return self.env.config

    @property
    def user_env(self):
        return self.env.user_env

    def map_folders(self) -> None:
        self.env.mapped_folders = [
            MappedPath(
                local=self.config.odoo_src_dir, docker=self.config.docker_odoo_dir
            ),
            MappedPath(local=self.config.venv_dir, docker=self.config.docker_venv_dir),
            MappedPath(
                local=self.config.odoo_tests_dir,
                docker=self.config.docker_temp_tests_dir,
            ),
            MappedPath(
                local=os.path.join(self.config.program_dir, constants.DEV_PROJECT_DIR),
                docker=self.config.docker_dev_project_dir,
            ),
            MappedPath(
                local=self.user_env.backups, docker=self.config.docker_backups_dir
            ),
            MappedPath(
                local=os.path.join(self.config.dir_for_odoo_container_home, ".local"),
                docker=str(
                    pathlib.PurePosixPath(self.config.docker_project_dir, ".local")
                ),
            ),
            MappedPath(
                local=os.path.join(self.config.dir_for_odoo_container_home, ".cache"),
                docker=str(
                    pathlib.PurePosixPath(self.config.docker_project_dir, ".cache")
                ),
            ),
        ]
        if self.config.developing_project.project_path:
            self.env.mapped_folders.append(
                MappedPath(
                    local=self.config.developing_project.project_path,
                    docker=self.config.docker_odoo_project_dir_path,
                ),
            )
        resolution = self._resolve_dependencies()
        self._dependency_resolution = resolution
        self.config.dependencies = resolution.urls
        if resolution.transitive_requirements or resolution.nested_fragments:
            self.config.apply_transitive_requirements(
                resolution.transitive_requirements,
                nested_fragments=resolution.nested_fragments,
            )
        materialize_deps = not self.config.skip_git_update()
        deps_materialized_during_discovery = (
            materialize_deps and self.config.use_oca_dependencies
        )
        for dependency_string in resolution.urls:
            dependency_project = self.config.handle_git_link(
                dependency_string,
                materialize=materialize_deps and not deps_materialized_during_discovery,
            )
            if not dependency_project.is_cloned:
                continue
            list_of_subprojects = self.config.check_project_for_subprojects(
                dependency_project.project_path
            )
            docker_dependency_project_path = str(
                pathlib.PurePosixPath(
                    self.config.docker_extra_addons,
                    dependency_project.inside_docker_path,
                )
            )
            self.config.dependencies_projects.append(dependency_project)
            self.config.dependencies_dirs.append(dependency_project.project_path)
            docker_dir_with_addons = docker_dependency_project_path
            if (
                dependency_project.project_data.project_type
                == constants.TYPE_PROJECT_MODULE
            ):
                docker_dir_with_addons = str(
                    pathlib.PurePosixPath(docker_dir_with_addons, os.pardir)
                )
            if list_of_subprojects:
                self.config.catalogs_of_modules_data.extend(list_of_subprojects)
                for subproject in list_of_subprojects:
                    self.config.docker_dirs_with_addons.append(
                        str(
                            pathlib.PurePosixPath(
                                docker_dir_with_addons, subproject.subproject_rel_path
                            )
                        )
                    )
            else:
                self.config.docker_dirs_with_addons.append(docker_dir_with_addons)
            self.env.mapped_folders.append(
                MappedPath(
                    local=dependency_project.project_path,
                    docker=docker_dependency_project_path,
                )
            )
        for pre_commit_file in self.config.pre_commit_map_files:
            real_file_place = os.path.join(
                self.config.developing_project_dir_path, pre_commit_file
            )
            if os.path.exists(real_file_place):
                full_path_pre_commit_file = os.path.join(
                    self.config.project_dir, pre_commit_file
                )
                if not os.path.exists(full_path_pre_commit_file):
                    shutil.copy(real_file_place, full_path_pre_commit_file)
                self.env.mapped_folders.append(
                    MappedPath(
                        local=full_path_pre_commit_file,
                        docker=str(
                            pathlib.PurePosixPath(
                                self.config.docker_odoo_project_dir_path,
                                pre_commit_file,
                            )
                        ),
                    )
                )
            else:
                _logger.warning(
                    translations.get_translation(
                        translations.PRE_COMMIT_FILE_WAS_NOT_FOUND
                    ).format(
                        PRE_COMMIT_FILE=pre_commit_file,
                        ODOO_PROJECT_DIR_PATH=self.config.developing_project_dir_path,
                    )
                )

    def _discover_dependency_extensions(
        self, dependency_string: str
    ) -> DependencyDiscovery:
        materialize = not self.config.skip_git_update()
        project = self.config.handle_git_link(
            dependency_string,
            materialize=materialize,
        )
        if not project.is_cloned:
            _logger.warning(
                translations.get_translation(
                    translations.OCA_DEPENDENCY_NOT_CLONED
                ).format(DEPENDENCY_URL=dependency_string)
            )
            return DependencyDiscovery()
        self.checkout_project(project)
        urls = read_oca_dependency_urls(project.project_path)
        nested = read_nested_odpm_fragment(project.project_path)
        if nested is None:
            return DependencyDiscovery(urls=urls)
        merged_urls = list(urls)
        seen_urls = set(urls)
        for dependency_url in nested.dependencies:
            if dependency_url in seen_urls:
                continue
            seen_urls.add(dependency_url)
            merged_urls.append(dependency_url)
        return DependencyDiscovery(
            urls=merged_urls,
            requirements=list(nested.requirements_txt),
            nested_fragment=nested,
        )

    def _resolve_dependencies(self) -> DependencyResolutionResult:
        seed_urls = list(self.config.dependencies)
        if self.config.skip_git_update() or not self.config.use_oca_dependencies:
            return DependencyResolutionResult(
                urls=seed_urls,
                transitive_requirements=[],
                nested_fragments=[],
            )

        initial_extra_urls: list[str] = []
        if self.config.developing_project.project_path:
            self.checkout_project(self.config.developing_project)
            initial_extra_urls = read_oca_dependency_urls(
                self.config.developing_project.project_path
            )

        return resolve_dependencies(
            seed_urls,
            self._discover_dependency_extensions,
            initial_extra_urls=initial_extra_urls,
        )

    def _should_checkout_developing(self, lock_manager=None) -> bool:
        developing = self.config.developing_project
        if not is_remote_git_link(developing):
            return False
        if lock_manager is not None and lock_manager.is_pinned(developing):
            return True
        return bool(developing.branch_explicit or developing.commit_explicit)

    def checkout_dependencies(self, lock_manager=None) -> None:
        list_for_checkout = [self.config.odoo_platform_project]
        if self._should_checkout_developing(lock_manager):
            list_for_checkout.append(self.config.developing_project)
        list_for_checkout.extend(self.config.dependencies_projects)
        for project in list_for_checkout:
            self.checkout_project(project, lock_manager=lock_manager)

    def checkout_project(
        self, project: HandleOdooProjectLink, *, lock_manager=None
    ) -> None:
        update_git_repos = self.config.update_git_repos
        if lock_manager is not None and lock_manager.is_pinned(project):
            update_git_repos = False
        project.checkout_repository(
            self.config.odoo_version,
            clean_git_repos=self.config.clean_git_repos,
            update_git_repos=update_git_repos,
        )

    def update_links(self) -> None:
        def delete_old_links(dir_to_clean: str, current_links) -> None:
            if not os.path.isdir(dir_to_clean):
                return
            for item in os.listdir(dir_to_clean):
                link_path = os.path.join(dir_to_clean, item)
                if os.path.islink(link_path) and item not in current_links:
                    os.unlink(link_path)

        def create_new_links(dir_to_create: str, current_links) -> None:
            os.makedirs(dir_to_create, exist_ok=True)
            for dep_for_link in current_links:
                dep_dir_name = os.path.basename(dep_for_link)
                link_path = os.path.join(dir_to_create, dep_dir_name)
                try:
                    os.symlink(dep_for_link, link_path)
                    self.config.symlinks_sources.append(
                        SymlinksSources(
                            source_path=dep_for_link,
                            link_path=os.path.join(
                                dep_for_link, link_path
                            ),
                        )
                    )
                except FileExistsError:
                    pass

        if (
            not os.path.exists(self.config.dependencies_dir)
            and self.config.dependencies_dirs
        ):
            os.mkdir(self.config.dependencies_dir)
        delete_old_links(self.config.project_dir, self.config.list_for_symlinks)
        create_new_links(self.config.project_dir, self.config.list_for_symlinks)
        if self.config.dependencies_dirs:
            delete_old_links(
                self.config.dependencies_dir, self.config.dependencies_dirs
            )
            create_new_links(
                self.config.dependencies_dir, self.config.dependencies_dirs
            )
        list_of_all_modules = []
        for catalog_of_modules in self.config.catalogs_of_modules_data:
            list_of_all_modules.extend(catalog_of_modules.list_of_modules)

        if list_of_all_modules:
            odoo_src_addons_dir = os.path.join(
                self.config.odoo_src_dir, self.config.platform_name, "addons"
            )
            delete_old_links(odoo_src_addons_dir, list_of_all_modules)
            if self.config.create_module_links:
                create_new_links(odoo_src_addons_dir, list_of_all_modules)
