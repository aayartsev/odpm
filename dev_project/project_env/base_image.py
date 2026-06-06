from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .. import constants, translations
from ..errors import PipelineError
from ..logging import get_module_logger
from ..subprocess_runner import run_checked, run_logged
from .base_image_identity import (
    base_image_identity_matches,
    expected_base_image_identity,
    read_base_image_identity,
    write_base_image_identity,
)

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
        image_exists = self.base_image_exists()
        identity_matches = base_image_identity_matches(self.config)
        if image_exists and identity_matches:
            return
        if image_exists and not identity_matches:
            if read_base_image_identity(self.config.project_dir) is None:
                _logger.info(
                    "Base image %s has no identity stamp; rebuilding to record "
                    "runtime identity",
                    self.config.odoo_image_name,
                )
            else:
                _logger.info(
                    "Base image %s was built for a different runtime identity; "
                    "rebuilding",
                    self.config.odoo_image_name,
                )
        self.build_base_image()
        write_base_image_identity(
            self.config.project_dir,
            expected_base_image_identity(self.config),
        )
