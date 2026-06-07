from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from .. import constants, translations
from ..project_dir_manager import template_needs_upgrade
from ..config.payload import runtime_config_path
from ..logging import get_module_logger
from .command_render import (
    render_compose_command_block,
    render_odpm_config_path_env_line,
)

if TYPE_CHECKING:
    from ..project_env.environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)


class ComposeGenerator:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    @property
    def user_env(self):
        return self.env.user_env

    def _ensure_compose_template_current(self, template_path: str) -> list[str]:
        if template_needs_upgrade(
            template_path, constants.COMPOSE_TEMPLATE_MARKERS
        ):
            _logger.info(
                "Upgrading %s to scenario-aware docker-compose template",
                template_path,
            )
            self.config.pd_manager.rebuild_docker_compose_template()
        with open(template_path) as template_file:
            return template_file.readlines()

    def _build_odoo_volumes_block(self, compose_service) -> str:
        volume_lines: list[str] = []
        if compose_service.include_runtime_config:
            local_runtime_config_path = runtime_config_path(self.config.project_dir)
            volume_lines.append(
                " " * 6
                + f"- {local_runtime_config_path}:{constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}:ro"
            )
        if self.config.policy.include_odoo_volumes:
            for mapped_volume in self.env.mapped_folders:
                volume_lines.append(
                    " " * 6 + f"- {mapped_volume.local}:{mapped_volume.docker}:Z"
                )
                if not os.path.exists(mapped_volume.local):
                    Path(mapped_volume.local).mkdir(
                        parents=True, exist_ok=True
                    )
        if not volume_lines:
            return ""
        return "    volumes:\n" + "\n".join(volume_lines) + "\n"

    def render_docker_compose_content(self) -> str:
        docker_compose_template_path = os.path.join(
            self.config.project_dir,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        lines = self._ensure_compose_template_current(docker_compose_template_path)

        policy = self.config.policy
        odoo_image = getattr(self.config, policy.odoo_image_attr)

        postgres_port = self.user_env.postgres_port or constants.POSTGRES_DEFAULT_PORT
        postgres_port_map = policy.build_postgres_port_map(
            f"{postgres_port}:{constants.POSTGRES_DOCKER_PORT}"
        )
        debugger_port = self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT
        debugger_port_map = f"{debugger_port}:{constants.DEBUGGER_DOCKER_PORT}"
        dev_extra_ports = policy.build_dev_extra_ports(debugger_port_map)

        compose_service = self.config.compose_service
        if compose_service is None:
            raise ValueError(
                "config.compose_service is required; run ComposeServiceBuilder.build() first"
            )

        odoo_volumes_block = self._build_odoo_volumes_block(compose_service)

        odpm_config_path_env_line = ""
        if compose_service.include_runtime_config:
            odpm_config_path_env_line = render_odpm_config_path_env_line(
                constants.ODPM_CONFIG_PATH_ENV,
                constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH,
            )

        compose_user = policy.runtime_unix_user()
        content = "".join(lines).format(
            ODOO_IMAGE=odoo_image,
            DEV_EXTRA_PORTS=dev_extra_ports,
            ODOO_VOLUMES_BLOCK=odoo_volumes_block,
            ODOO_PORT=self.user_env.odoo_port or constants.ODOO_DEFAULT_PORT,
            POSTGRES_PORT_MAP=postgres_port_map,
            GEVENT_PORT=self.user_env.gevent_port or constants.GEVENT_DEFAULT_PORT,
            DOCKER_PROJECT_DIR=compose_service.working_dir,
            ODPM_CONFIG_PATH_ENV_LINE=odpm_config_path_env_line,
            START_COMMAND_BLOCK=render_compose_command_block(
                compose_service.command
            ),
            COMPOSE_USER=compose_user,
            CONTAINER_USER=compose_user,
            CONTAINER_PASSWORD=constants.CONTAINER_PASSWORD,
            CURRENT_USER=compose_user,
            CURRENT_PASSWORD=constants.CONTAINER_PASSWORD,
            POSTGRES_ODOO_USER=constants.POSTGRES_ODOO_USER,
            POSTGRES_ODOO_PASS=constants.POSTGRES_ODOO_PASS,
            ODOO_DOCKER_PORT=constants.ODOO_DOCKER_PORT,
            DEBUGGER_DOCKER_PORT=constants.DEBUGGER_DOCKER_PORT,
            GEVENT_DOCKER_PORT=constants.GEVENT_DOCKER_PORT,
            COMPOSE_FILE_VERSION=self.config.compose_file_version,
            DATABASE_NAME_INSTANCE=constants.DATABASE_NAME_INSTANCE,
            POSTGRES_VERSION=self.config.postgres_version,
            POSTGRES_DATA_LOCAL_STORAGE=self.config.postgres_data_local_storage,
            DEBUGGER_PORT_MAP=debugger_port_map,
        )
        return content.replace(
            constants.MESSAGE_MARKER,
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )

    def generate_docker_compose_file(self) -> None:
        content = self.render_docker_compose_content()
        docker_compose_path = os.path.join(self.config.project_dir, "docker-compose.yml")
        with open(docker_compose_path, "w") as writer:
            writer.write(content)
