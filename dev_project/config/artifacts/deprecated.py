"""Legacy config.json migration and deprecated template placeholder detection."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from ... import constants, translations
from ...logging import get_module_logger

if TYPE_CHECKING:
    from ..config import Config

_logger = get_module_logger(__name__)


class DeprecatedConfigHandler:
    def __init__(self, config: Config) -> None:
        self.config = config

    def check_for_config(self) -> None:
        self.config.config_json_path = os.path.join(
            self.config.project_dir, constants.CONFIG_FILE_NAME
        )
        self.config.config_deprecated_json_path = os.path.join(
            self.config.project_dir, f"deprecated_{constants.CONFIG_FILE_NAME}"
        )
        if os.path.exists(self.config.config_json_path):
            with open(self.config.config_json_path) as config_file:
                self.config.config_json_content = json.load(config_file)
            os.rename(self.config.config_json_path, self.config.config_deprecated_json_path)
            _logger.warning(
                translations.get_translation(
                    translations.CONFIG_JSON_IS_DEPRECATED
                ).format(
                    CONFIG_FILE_NAME=constants.CONFIG_FILE_NAME,
                )
            )

    def check_file_for_deprecated_words(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            return
        with open(file_path) as f:
            lines = f.readlines()
        remove_file = False
        for line in lines:
            for word in constants.DEPRECATED_WORDS:
                if word.lower() in line.lower():
                    remove_file = True
                    break
        if remove_file:
            dir_fo_file = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            deprecated_filename = f"deprecated_{filename}"
            _logger.warning(
                translations.get_translation(
                    translations.FILE_WITH_DEPRECATED_CONTEND_WAS_RENAMED
                ).format(
                    SOURCE_FILE=file_path,
                    DEPRECATED_FILE_NAME=deprecated_filename,
                )
            )
            os.rename(file_path, os.path.join(dir_fo_file, deprecated_filename))
