from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from .. import constants, translations
from ..errors import PipelineError
from ..inside_docker_app.logger import get_module_logger
from ..subprocess_runner import run_checked, run_logged

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)


class BaseImageBuilder:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def base_image_exists(self) -> bool:
        result = run_checked(["docker", "images", "--format", "'{{json .}}'"])
        for record in result.stdout.split("\n"):
            if not record:
                continue
            new_record = json.loads(record.replace("'", ""))
            if self.config.odoo_image_name == new_record.get("Repository"):
                return True
        return False

    def build_base_image(self) -> None:
        os.chdir(self.config.project_dir)
        returncode = run_logged(
            [
                "docker",
                "build",
                "-f",
                self.config.dockerfile_path,
                "-t",
                self.config.odoo_image_name,
                f"--platform=linux/{self.config.arch}",
                self.config.project_dir,
            ],
            cwd=self.config.project_dir,
        )
        if returncode != 0:
            message = translations.get_translation(
                translations.DOCKER_BUILD_FAILED
            ).format(EXIT_CODE=returncode)
            _logger.error(message)
            raise PipelineError(message, exit_code=returncode)

    def ensure_base_image(self) -> None:
        if not self.base_image_exists():
            self.build_base_image()
