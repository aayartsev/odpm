from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ..translations import _
from ..errors import PipelineError, SubprocessError
from ..logging import get_module_logger
from ..subprocess_runner import run_logged, run_or_raise
from .base_image_identity import (
    base_image_identity_matches,
    expected_base_image_identity,
    read_base_image_identity,
    write_base_image_identity,
)

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)


def _identity_mismatch_reason(config) -> str | None:
    stamp = read_base_image_identity(config.project_dir)
    expected = expected_base_image_identity(config)
    if stamp is None:
        return "missing identity stamp"
    if stamp.get("base_image_profile") != expected.get("base_image_profile"):
        return (
            f"base image profile changed "
            f"({stamp.get('base_image_profile')!r} -> {expected.get('base_image_profile')!r})"
        )
    if stamp.get("dockerfile_sha256") != expected.get("dockerfile_sha256"):
        return "dockerfile changed (sha256 mismatch)"
    if (
        stamp.get("user") != expected.get("user")
        or stamp.get("uid") != expected.get("uid")
        or stamp.get("gid") != expected.get("gid")
    ):
        return "runtime Unix identity changed"
    return None


class BaseImageBuilder:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def base_image_exists(self) -> bool:
        try:
            result = run_or_raise(["docker", "images", "--format", "'{{json .}}'"])
        except SubprocessError:
            return False
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
            message = _('docker build failed with exit code {EXIT_CODE}').format(EXIT_CODE=returncode)
            _logger.error(message)
            raise PipelineError(message, exit_code=returncode)

    def ensure_base_image(self) -> None:
        image_exists = self.base_image_exists()
        identity_matches = base_image_identity_matches(self.config)
        if image_exists and identity_matches:
            return
        if image_exists and not identity_matches:
            reason = _identity_mismatch_reason(self.config)
            if reason:
                _logger.info(
                    "Base image %s stale: %s; rebuilding",
                    self.config.odoo_image_name,
                    reason,
                )
            elif read_base_image_identity(self.config.project_dir) is None:
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
