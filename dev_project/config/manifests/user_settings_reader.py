"""Read and bootstrap user_settings.json paths and content."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ... import constants

if TYPE_CHECKING:
    from ..config import Config


class UserSettingsReader:
    def __init__(
        self,
        config: Config,
        *,
        create_default_user_settings: Callable[[], Any],
    ) -> None:
        self.config = config
        self._create_default_user_settings = create_default_user_settings

    def get_user_settings_json(self) -> None:
        self.config.user_settings_json = os.path.join(
            self.config.project_dir, constants.USER_CONFIG_FILE_NAME
        )
        if not os.path.exists(self.config.user_settings_json):
            default_user_settings_json_content = self._create_default_user_settings()
            with open(
                self.config.user_settings_json, "w", encoding="utf-8"
            ) as user_settings_json_file:
                json.dump(
                    default_user_settings_json_content,
                    user_settings_json_file,
                    ensure_ascii=False,
                    indent=4,
                )

    def get_user_settings(self) -> None:
        if os.path.exists(self.config.user_settings_json):
            with open(self.config.user_settings_json) as user_settings_file:
                self.config._raw_user_settings = json.load(user_settings_file)
