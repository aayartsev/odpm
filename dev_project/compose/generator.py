from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from ..translations import _
from ..project_dir_manager import template_needs_upgrade
from ..logging import get_module_logger
from ..yaml import dump_document
from .compose_document import build_compose_document
from .validate import validate_compose_document

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
    def host_ctx(self):
        return self.env.host_ctx

    @property
    def user_env(self):
        return self.env.user_env

    def _ensure_compose_template_current(self, template_path: str) -> None:
        if template_needs_upgrade(
            template_path, constants.COMPOSE_TEMPLATE_MARKERS
        ):
            _logger.info(
                "Upgrading %s to scenario-aware docker-compose template",
                template_path,
            )
            self.config.pd_manager.rebuild_docker_compose_template()

    def render_docker_compose_content(self) -> str:
        docker_compose_template_path = os.path.join(
            self.host_ctx.project_dir,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        self._ensure_compose_template_current(docker_compose_template_path)

        document = build_compose_document(self.env)
        validate_compose_document(document)
        header = f"# {_('Do not change this file, its content is generating automatically')}\n\n"
        return header + dump_document(document)

    def generate_docker_compose_file(self) -> None:
        content = self.render_docker_compose_content()
        docker_compose_path = os.path.join(self.host_ctx.project_dir, "docker-compose.yml")
        with open(docker_compose_path, "w") as writer:
            writer.write(content)
