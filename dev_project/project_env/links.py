from __future__ import annotations

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from .. import constants, translations
from ..dependency_resolver import read_oca_dependency_urls, resolve_dependency_urls
from ..git import HandleOdooProjectLink
from ..inside_docker_app.logger import get_module_logger
from .types import MappedPath, SymlinksSources

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)


class ProjectLinks:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

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
        resolved_dependencies = self._resolve_dependencies()
        self.config.dependencies = resolved_dependencies
        materialize_deps = not self.config.skip_git_update()
        for dependency_string in resolved_dependencies:
            dependency_project = self.config.handle_git_link(
                dependency_string,
                materialize=materialize_deps,
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

    def _get_oca_urls_for_dependency(self, dependency_string: str) -> list[str]:
        project = self.config.handle_git_link(dependency_string)
        if not project.is_cloned:
            _logger.warning(
                translations.get_translation(
                    translations.OCA_DEPENDENCY_NOT_CLONED
                ).format(DEPENDENCY_URL=dependency_string)
            )
            return []
        self.checkout_project(project)
        return read_oca_dependency_urls(project.project_path)

    def _resolve_dependencies(self) -> list[str]:
        seed_urls = list(self.config.dependencies)
        if self.config.skip_git_update() or not self.config.use_oca_dependencies:
            return seed_urls

        initial_extra_urls: list[str] = []
        if self.config.developing_project.project_path:
            self.checkout_project(self.config.developing_project)
            initial_extra_urls = read_oca_dependency_urls(
                self.config.developing_project.project_path
            )

        return resolve_dependency_urls(
            seed_urls,
            self._get_oca_urls_for_dependency,
            initial_extra_urls=initial_extra_urls,
        )

    def checkout_dependencies(self, lock_manager=None) -> None:
        list_for_checkout = [self.config.odoo_platform_project]
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
