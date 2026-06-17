from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from ..translations import _
from ..config.odoo_conf import odoo_conf_on_disk_needs_regeneration

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment


class ProjectTemplates:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def generate_dockerfile(self) -> None:
        policy = self.config.policy
        with open(self.config.project_dockerfile_template_path) as reader:
            content = reader.read()
        content = content.format(
            PROCESSOR_ARCH=self.config.arch,
            CONTAINER_USER_UID=policy.runtime_unix_uid(),
            CONTAINER_USER_GID=policy.runtime_unix_gid(),
            CONTAINER_USER=policy.runtime_unix_user(),
            CONTAINER_PASSWORD=policy.runtime_unix_password(),
            CURRENT_USER_UID=policy.runtime_unix_uid(),
            CURRENT_USER_GID=policy.runtime_unix_gid(),
            CURRENT_USER=policy.runtime_unix_user(),
            CURRENT_PASSWORD=policy.runtime_unix_password(),
            PYTHON_VERSION=self.config.python_version,
            DISTRO_NAME=self.config.distro_name,
            DISTRO_VERSION=self.config.distro_version,
            DISTRO_VERSION_CODENAME=self.config.distro_version_codename,
        )
        content = content.replace(
            _('If you want drop this file to default values, just delete it'),
            _('Do not change this file, its content is generating automatically'),
        )
        dockerfile_path = os.path.join(self.config.project_dir, constants.DOCKERFILE)
        self.config.dockerfile_path = dockerfile_path
        with open(dockerfile_path, "w") as writer:
            writer.write(content)

    def generate_dockerignore(self) -> None:
        with open(self.config.project_dockerignore_template_path) as reader:
            content = reader.read()
        content = content.replace(
            _('If you want drop this file to default values, just delete it'),
            _('Do not change this file, its content is generating automatically'),
        )
        dockerignore_path = os.path.join(self.config.project_dir, constants.DOCKERIGNORE)
        with open(dockerignore_path, "w") as writer:
            writer.write(content)

    def generate_config_file(self) -> None:
        config_file_template_path = os.path.join(
            self.config.project_dir,
            constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        )
        with open(config_file_template_path) as reader:
            content = reader.read()
        for replace_phrase in {
            constants.DO_NOT_CHANGE_PARAM: _('Do not change this param, it is generating automatically'),
            constants.ADMIN_PASSWD_MESSAGE: _('Do not change, it will get from "db_manager_password" param from config.json file'),
            constants.MESSAGE_MARKER: _('If you want drop this file to default values, just delete it'),
            constants.POSTGRES_ODOO_USER_MARKER: constants.POSTGRES_ODOO_USER,
            constants.POSTGRES_ODOO_PASS_MARKER: constants.POSTGRES_ODOO_PASS,
            constants.POSTGRES_ODOO_HOST_MARKER: self.config.user_env.postgres_service_name,
            constants.POSTGRES_ODOO_PORT_MARKER: str(constants.POSTGRES_ODOO_PORT),
            constants.ODOO_PORT_MARKER: str(constants.ODOO_DOCKER_PORT),
        }.items():
            content = content.replace(replace_phrase[0], replace_phrase[1])
        if odoo_conf_on_disk_needs_regeneration(
            self.config.path_odoo_conf
        ) or self.config.pd_manager.check_project_odoo_config_template(
            config_file_template_path
        ):
            with open(self.config.path_odoo_conf, "w") as writer:
                writer.write(content)
