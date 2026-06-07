"""Read and bootstrap odpm.json paths, migration, and content."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from typing import TYPE_CHECKING

from ... import constants

if TYPE_CHECKING:
    from ..config import Config


class OdpmJsonReader:
    def __init__(
        self,
        config: Config,
        *,
        rewrite_odpm_json: Callable[[], None],
    ) -> None:
        self.config = config
        self._rewrite_odpm_json = rewrite_odpm_json

    def get_project_odpm_json(self) -> None:
        self.config.repo_odpm_json = os.path.join(
            self.config.developing_project.project_path,
            constants.PROJECT_CONFIG_FILE_NAME,
        )
        self.config.project_odpm_json = os.path.join(
            self.config.project_dir, constants.PROJECT_CONFIG_FILE_NAME
        )
        if not os.path.exists(self.config.repo_odpm_json) and not os.path.exists(
            self.config.project_odpm_json
        ):
            self._rewrite_odpm_json()

    def get_odpm_settings(self) -> None:
        if os.path.exists(self.config.project_odpm_json) and not os.path.exists(
            self.config.repo_odpm_json
        ):
            shutil.move(self.config.project_odpm_json, self.config.repo_odpm_json)
        if (
            not os.path.islink(self.config.project_odpm_json)
            and os.path.exists(self.config.project_odpm_json)
            and os.path.exists(self.config.repo_odpm_json)
        ):
            os.rename(
                self.config.project_odpm_json,
                f"deprecated_{constants.PROJECT_CONFIG_FILE_NAME}",
            )
        if not os.path.exists(self.config.repo_odpm_json):
            self._rewrite_odpm_json()
        with open(self.config.repo_odpm_json) as repo_odpm_json:
            self.config._raw_odpm_json = json.load(repo_odpm_json)
