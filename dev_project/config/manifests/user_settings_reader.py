"""Read and bootstrap user_settings.json paths and content."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ... import constants
from ...security_profiles import (
    HARDENED_DB_DEFAULT_ADMIN_PASSWORD_REF,
    HARDENED_DB_MANAGER_PASSWORD_REF,
    SECURITY_PROFILE_HARDENED,
)
from ..transforms.env_substitution import (
    USER_SETTINGS_ENV_EXPAND_FIELDS,
    expand_env_deep,
    expand_env_in_json,
)

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
            policy = getattr(self.config, "policy", None)
            if (
                policy is not None
                and getattr(policy, "security_profile", None) == SECURITY_PROFILE_HARDENED
                and getattr(policy, "should_bootstrap_odoo_password_secrets", lambda: False)()
            ):
                self.config.bootstrap.wrote_hardened_password_defaults = True

    def get_user_settings_phase1(self) -> None:
        """Load disk raw; expand only pre-manifest fields (``developing_project``)."""
        if not os.path.exists(self.config.user_settings_json):
            return
        with open(self.config.user_settings_json, encoding="utf-8") as user_settings_file:
            raw = json.load(user_settings_file)
        if not isinstance(raw, dict):
            raw = {}
        self.config.bootstrap.raw_user_settings_disk = dict(raw)
        self.config._raw_user_settings = expand_env_in_json(
            raw,
            resolver=self.config.env_resolver,
            allowed_fields=USER_SETTINGS_ENV_EXPAND_FIELDS,
        )

    def get_user_settings(self) -> None:
        """Backward-compatible alias for phase 1 load."""
        self.get_user_settings_phase1()

    def get_user_settings_phase2(self) -> None:
        """Deep-expand all string leaves after secrets are available."""
        disk = getattr(self.config.bootstrap, "raw_user_settings_disk", None)
        if not isinstance(disk, dict):
            return
        self.config._raw_user_settings = expand_env_deep(
            disk,
            resolver=self.config.env_resolver,
            field_path="user_settings",
        )


def hardened_password_defaults() -> tuple[str, str]:
    return HARDENED_DB_MANAGER_PASSWORD_REF, HARDENED_DB_DEFAULT_ADMIN_PASSWORD_REF
