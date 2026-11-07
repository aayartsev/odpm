from __future__ import annotations

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from .. import constants
from ..translations import _
from ..dependency_resolver import DependencyResolutionResult
from ..logging import get_module_logger
from .types import MappedPath

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)

class VolumeMapper:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def user_env(self):
        return self.env.user_env

    def build_base_folders(self) -> list[MappedPath]:
        host_ctx = self.env.host_ctx
        config = self.env.bootstrap.config
        layout = host_ctx.docker_layout
        mapped_folders = [
            MappedPath(
                local=config.odoo_src_dir,
                docker=layout.docker_odoo_dir,
            ),
            MappedPath(
                local=layout.venv_dir,
                docker=layout.docker_venv_dir,
            ),
            MappedPath(
                local=layout.odoo_tests_dir,
                docker=layout.docker_temp_tests_dir,
            ),
            MappedPath(
                local=os.path.join(host_ctx.program_dir, constants.DEV_PROJECT_DIR),
                docker=layout.docker_dev_project_dir,
            ),
            MappedPath(
                local=self.user_env.backups,
                docker=layout.docker_backups_dir,
            ),
            MappedPath(
                local=os.path.join(
                    layout.dir_for_odoo_container_home, ".local"
                ),
                docker=str(
                    pathlib.PurePosixPath(
                        layout.docker_project_dir, ".local"
                    )
                ),
            ),
            MappedPath(
                local=os.path.join(
                    layout.dir_for_odoo_container_home, ".cache"
                ),
                docker=str(
                    pathlib.PurePosixPath(
                        layout.docker_project_dir, ".cache"
                    )
                ),
            ),
        ]
        if config.developing_project.project_path:
            mapped_folders.append(
                MappedPath(
                    local=config.developing_project.project_path,
                    docker=layout.docker_odoo_project_dir_path,
                ),
            )
        return mapped_folders

    def append_dependency_mounts(
        self,
        resolution: DependencyResolutionResult,
        *,
        materialize_deps: bool,
        skip_materialize: bool,
    ) -> None:
        host_ctx = self.env.host_ctx
        config = self.env.bootstrap.config
        layout = host_ctx.docker_layout
        for dependency_string in resolution.urls:
            materialize = materialize_deps and not skip_materialize
            dependency_project = config.handle_git_link(
                dependency_string,
                materialize=materialize,
            )
            try:
                if skip_materialize and not dependency_project.is_cloned:
                    dependency_project.build_project()
            finally:
                if dependency_project.project_path:
                    config.ensure_git_repo_symlink(
                        dependency_project.project_path,
                        scope="dependency",
                    )
            if not dependency_project.is_cloned:
                continue
            list_of_subprojects = config.check_project_for_subprojects(
                dependency_project.project_path
            )
            docker_dependency_project_path = str(
                pathlib.PurePosixPath(
                    layout.docker_extra_addons,
                    dependency_project.inside_docker_path,
                )
            )
            layout.dependencies_projects.append(dependency_project)
            layout.dependencies_dirs.append(
                dependency_project.project_path
            )
            docker_dir_with_addons = docker_dependency_project_path
            if (
                dependency_project.project_data.project_type
                == constants.TYPE_PROJECT_MODULE
            ):
                docker_dir_with_addons = str(
                    pathlib.PurePosixPath(docker_dir_with_addons, os.pardir)
                )
            if list_of_subprojects:
                host_ctx.addon_layout.catalogs_of_modules_data.extend(
                    list_of_subprojects
                )
                for subproject in list_of_subprojects:
                    layout.docker_dirs_with_addons.append(
                        str(
                            pathlib.PurePosixPath(
                                docker_dir_with_addons, subproject.subproject_rel_path
                            )
                        )
                    )
            else:
                layout.docker_dirs_with_addons.append(
                    docker_dir_with_addons
                )
            self.env.mapped_folders.append(
                MappedPath(
                    local=dependency_project.project_path,
                    docker=docker_dependency_project_path,
                )
            )

    def map_pre_commit_files(self) -> None:
        host_ctx = self.env.host_ctx
        config = self.env.bootstrap.config
        for pre_commit_file in host_ctx.user_settings.pre_commit_map_files:
            real_file_place = os.path.join(
                config.developing_project_dir_path, pre_commit_file
            )
            if os.path.exists(real_file_place):
                full_path_pre_commit_file = os.path.join(
                    host_ctx.project_dir, pre_commit_file
                )
                if not os.path.exists(full_path_pre_commit_file):
                    shutil.copy(real_file_place, full_path_pre_commit_file)
                self.env.mapped_folders.append(
                    MappedPath(
                        local=full_path_pre_commit_file,
                        docker=str(
                            pathlib.PurePosixPath(
                                host_ctx.docker_layout.docker_odoo_project_dir_path,
                                pre_commit_file,
                            )
                        ),
                    )
                )
            else:
                _logger.warning(
                    _('Pre-commit file {PRE_COMMIT_FILE} was not found at {ODOO_PROJECT_DIR_PATH}').format(
                        PRE_COMMIT_FILE=pre_commit_file,
                        ODOO_PROJECT_DIR_PATH=config.developing_project_dir_path,
                    )
                )
