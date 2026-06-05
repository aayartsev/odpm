from __future__ import annotations

import os
from typing import TYPE_CHECKING

from . import constants, translations

if TYPE_CHECKING:
    from .host_project_env import CreateProjectEnvironment


class ProjectTemplates:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def generate_dockerfile(self) -> None:
        with open(self.config.project_dockerfile_template_path) as reader:
            content = reader.read()
        content = content.format(
            PROCESSOR_ARCH=self.config.arch,
            CURRENT_USER_UID=constants.CURRENT_USER_UID,
            CURRENT_USER_GID=constants.CURRENT_USER_GID,
            CURRENT_USER=constants.CURRENT_USER,
            CURRENT_PASSWORD=constants.CURRENT_PASSWORD,
            PYTHON_VERSION=self.config.python_version,
            DISTRO_NAME=self.config.distro_name,
            DISTRO_VERSION=self.config.distro_version,
            DISTRO_VERSION_CODENAME=self.config.distro_version_codename,
        )
        content = content.replace(
            translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )
        dockerfile_path = os.path.join(self.config.project_dir, constants.DOCKERFILE)
        self.config.dockerfile_path = dockerfile_path
        with open(dockerfile_path, "w") as writer:
            writer.write(content)

    def generate_dockerignore(self) -> None:
        with open(self.config.project_dockerignore_template_path) as reader:
            content = reader.read()
        content = content.replace(
            translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
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
            constants.DO_NOT_CHANGE_PARAM: translations.get_translation(
                translations.DO_NOT_CHANGE_PARAM
            ),
            constants.ADMIN_PASSWD_MESSAGE: translations.get_translation(
                translations.ADMIN_PASSWD_MESSAGE
            ),
            constants.MESSAGE_MARKER: translations.get_translation(
                translations.MESSAGE_FOR_TEMPLATES
            ),
            constants.POSTGRES_ODOO_USER_MARKER: constants.POSTGRES_ODOO_USER,
            constants.POSTGRES_ODOO_PASS_MARKER: constants.POSTGRES_ODOO_PASS,
            constants.POSTGRES_ODOO_HOST_MARKER: constants.POSTGRES_ODOO_HOST,
            constants.POSTGRES_ODOO_PORT_MARKER: str(constants.POSTGRES_ODOO_PORT),
            constants.ODOO_PORT_MARKER: str(constants.ODOO_DOCKER_PORT),
        }.items():
            content = content.replace(replace_phrase[0], replace_phrase[1])
        if not os.path.exists(
            self.config.path_odoo_conf
        ) or self.config.pd_manager.check_project_odoo_config_template(
            config_file_template_path
        ):
            with open(self.config.path_odoo_conf, "w") as writer:
                writer.write(content)

    def generate_vscode_settings_json(self) -> None:
        vscode_settings_json_template_path = os.path.join(
            self.config.project_dir, constants.PROJECT_VSCODE_SETTINGS_TEMPLATE
        )
        with open(vscode_settings_json_template_path) as reader:
            lines = reader.readlines()
        content = "".join(lines[1:]).replace(
            "{PYTHON_VERSION}",
            self.config.python_version,
        )
        content = content.replace(
            translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )
        vscode_settings_json_path = os.path.join(
            self.env.get_vscode_dir_path(), "settings.json"
        )
        with open(vscode_settings_json_path, "w") as writer:
            writer.write(content)
