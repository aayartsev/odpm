from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from .. import constants, translations
from ..config.odoo_conf import odoo_conf_on_disk_needs_regeneration
from .types import DebuggerPathRecord, DebuggerUnit

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment


class ProjectTemplates:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def get_vscode_dir_path(self) -> str:
        vscode_dir = os.path.join(self.config.project_dir, ".vscode")
        if not os.path.exists(vscode_dir):
            os.mkdir(vscode_dir)
        return vscode_dir

    def update_vscode_debugger_launcher(self) -> None:
        def get_list_of_mapped_sources() -> None:
            list_for_links = [
                symlink_item for symlink_item in self.config.symlinks_sources
            ]
            for linking_dir in list_for_links:
                dir_name_to_link = os.path.basename(linking_dir.link_path)
                for mapped_folder in self.env.mapped_folders:
                    mapped_dir_name = os.path.basename(mapped_folder.local)
                    if (
                        dir_name_to_link == mapped_dir_name
                        and linking_dir.source_path
                        not in [self.env.user_env.backups]
                    ):
                        self.config.debugger_path_mappings.append(
                            DebuggerPathRecord(
                                localRoot=linking_dir.link_path,
                                remoteRoot=mapped_folder.docker,
                            )
                        )

        launch_json = os.path.join(self.get_vscode_dir_path(), "launch.json")
        if not os.path.exists(launch_json):
            content = {"configurations": []}
        else:
            with open(launch_json, "r") as open_file:
                content = json.load(open_file)
        debugger_unit_exists = False
        get_list_of_mapped_sources()
        port = self.env.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT
        odoo_debugger_uint = DebuggerUnit(
            name=constants.DEBUGGER_UNIT_NAME,
            type="python",
            request="attach",
            port=int(port),
            host="localhost",
            pathMappings=self.config.debugger_path_mappings,
        )
        for index, debugger_unit in enumerate(content["configurations"]):
            if debugger_unit["name"] == constants.DEBUGGER_UNIT_NAME:
                content["configurations"][index] = odoo_debugger_uint
                debugger_unit_exists = True
        if not debugger_unit_exists:
            content["configurations"].append(
                DebuggerUnit(
                    name=constants.DEBUGGER_UNIT_NAME,
                    type="python",
                    request="attach",
                    port=self.env.user_env.debugger_port
                    or constants.DEBUGGER_DEFAULT_PORT,
                    host="localhost",
                    pathMappings=self.config.debugger_path_mappings,
                )
            )
        with open(launch_json, "w") as outfile:
            json.dump(content, outfile, indent=4)

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
        if odoo_conf_on_disk_needs_regeneration(
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
            self.get_vscode_dir_path(), "settings.json"
        )
        with open(vscode_settings_json_path, "w") as writer:
            writer.write(content)
