from __future__ import annotations

import os
import pathlib
from typing import TYPE_CHECKING

from .. import constants

if TYPE_CHECKING:
    from .config import Config


class ConfigPaths:
    def __init__(self, config: Config) -> None:
        self.config = config

    def get_postgres_data_local_storage_path(self) -> str:
        postgres_data_local_storage_path = os.path.join(
            self.config.pd_manager.project_path, constants.POSTGRES_LOCAL_STORAGE_DIR
        )
        if not os.path.exists(postgres_data_local_storage_path):
            pathlib.Path(postgres_data_local_storage_path).mkdir(
                parents=True, exist_ok=True
            )
        return postgres_data_local_storage_path

    def get_odoo_ci_image_name(self) -> str:
        image_tag = getattr(self.config.arguments, "image_tag", None)
        if image_tag:
            return image_tag.strip()
        version_label = str(self.config.odoo_version).replace(".", "-")
        return f"{self.config.platform_name}-{version_label}-ci:latest"

    def apply_image_names(self) -> None:
        docker = self.config.docker_layout
        profile = self.config.policy.base_image_profile
        docker.odoo_image_name = (
            f"odoo-{self.config.arch}-python-{self.config.python_version}-"
            f"{self.config.distro_name}-"
            f"{self.config.distro_version.replace('.', '')}-{profile}"
        )
        docker.odoo_ci_image_name = self.get_odoo_ci_image_name()
        docker.ci_build_context_dir = os.path.join(
            self.config.project_dir, constants.CI_BUILD_CONTEXT_DIR
        )

    def apply_docker_layout(self) -> None:
        runtime_user = self.config.policy.runtime_unix_user()
        docker = self.config.docker_layout
        docker.docker_project_dir = str(
            pathlib.PurePosixPath("/home", runtime_user)
        )
        docker.docker_dev_project_dir = str(
            pathlib.PurePosixPath(docker.docker_project_dir, constants.DEV_PROJECT_DIR)
        )
        docker.docker_inside_app = str(
            pathlib.PurePosixPath(docker.docker_dev_project_dir, "inside_docker_app")
        )
        docker.docker_odoo_dir = str(
            pathlib.PurePosixPath(docker.docker_project_dir, self.config.platform_name)
        )
        docker.docker_extra_addons = str(
            pathlib.PurePosixPath(docker.docker_project_dir, "extra-addons")
        )
        docker.path_odoo_conf = os.path.join(
            self.config.project_dir, constants.ODOO_CONF_NAME
        )
        docker.docker_path_odoo_conf = str(
            pathlib.PurePosixPath(docker.docker_project_dir, constants.ODOO_CONF_NAME)
        )
        docker.docker_venv_dir = str(
            pathlib.PurePosixPath(docker.docker_project_dir, constants.VENV_DIR_NAME)
        )
        docker.docker_backups_dir = str(
            pathlib.PurePosixPath(docker.docker_project_dir, "backups")
        )
        docker.docker_temp_tests_dir = str(pathlib.PurePosixPath("/tmp", "odoo_tests"))
        docker.venv_dir = os.path.join(self.config.project_dir, constants.VENV_DIR_NAME)
        docker.dir_for_odoo_container_home = os.path.join(
            self.config.project_dir, "data/odoo", f"home/{runtime_user}"
        )
        os.makedirs(docker.dir_for_odoo_container_home, exist_ok=True)
        for subdir in (".cache", ".local"):
            os.makedirs(
                os.path.join(docker.dir_for_odoo_container_home, subdir),
                exist_ok=True,
            )
        docker.dependencies_dir = os.path.join(
            self.config.project_dir, constants.DEPENDENCIES_DIR
        )
        docker.odoo_tests_dir = os.path.join(
            self.config.project_dir, "data/odoo", "tmp/odoo_tests"
        )
        docker.compose_file_version = constants.DOCKER_COMPOSE_DEFAULT_FILE_VERSION
        docker.docker_compose_command = constants.DEFAULT_DOCKER_COMPOSE_COMMAND

    def apply_developing_project_docker_path(self) -> None:
        if not self.config.developing_project:
            return
        docker = self.config.docker_layout
        if (
            self.config.developing_project.project_data.project_type
            == constants.TYPE_PROJECT_MODULE
        ):
            docker.docker_odoo_project_dir_path = str(
                pathlib.PurePosixPath(
                    docker.docker_extra_addons,
                    self.config.developing_project.project_data.name,
                    self.config.developing_project.project_data.git_name,
                )
            )
        if (
            self.config.developing_project.project_data.project_type
            == constants.TYPE_PROJECT_PROJECT
        ):
            docker.docker_odoo_project_dir_path = str(
                pathlib.PurePosixPath(
                    docker.docker_extra_addons,
                    self.config.developing_project.project_data.name,
                )
            )

    def apply_symlink_sources(self) -> None:
        self.config.docker_layout.list_for_symlinks = [
            self.config.user_env.backups,
            self.config.odoo_src_dir,
            self.config.developing_project_dir_path,
            self.config.repo_odpm_json,
        ]
