from __future__ import annotations

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from .. import constants
from ..translations import _
from ..dependency_resolver import DependencyResolutionResult
from ..host.user_env_parse import process_env_with_dotenv
from ..logging import get_module_logger
from ..wheel_cache import host_cache_mounts
from ..golden_venv import host_golden_mounts
from .types import MappedPath

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)


class VolumeMapper:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    @property
    def user_env(self):
        return self.env.user_env

    def build_base_folders(self) -> list[MappedPath]:
        mapped_folders = [
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
        if self.config.policy.mount_runtime_config_from_host():
            dotenv = {}
            if hasattr(self.user_env, "project_dotenv_dict"):
                dotenv = self.user_env.project_dotenv_dict()
            cache_env = process_env_with_dotenv(dotenv)
            mapped_folders.extend(
                host_cache_mounts(
                    python_version=self.config.python_version,
                    env=cache_env,
                )
            )
            mapped_folders.extend(host_golden_mounts(env=cache_env))
        if self.config.developing_project.project_path:
            mapped_folders.append(
                MappedPath(
                    local=self.config.developing_project.project_path,
                    docker=self.config.docker_odoo_project_dir_path,
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
        for dependency_string in resolution.urls:
            materialize = materialize_deps and not skip_materialize
            dependency_project = self.config.handle_git_link(
                dependency_string,
                materialize=materialize,
            )
            try:
                if skip_materialize and not dependency_project.is_cloned:
                    dependency_project.build_project()
            finally:
                if dependency_project.project_path:
                    self.config.ensure_git_repo_symlink(
                        dependency_project.project_path,
                        scope="dependency",
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
                self.env.host_ctx.addon_layout.catalogs_of_modules_data.extend(
                    list_of_subprojects
                )
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

    def map_pre_commit_files(self) -> None:
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
                    _('Pre-commit file {PRE_COMMIT_FILE} was not found at {ODOO_PROJECT_DIR_PATH}').format(
                        PRE_COMMIT_FILE=pre_commit_file,
                        ODOO_PROJECT_DIR_PATH=self.config.developing_project_dir_path,
                    )
                )
