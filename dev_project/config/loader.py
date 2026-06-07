from __future__ import annotations

import json
import pathlib
from typing import TYPE_CHECKING

from .. import constants
from .artifacts import DeprecatedConfigHandler
from .defaults import ConfigDefaultsFactory
from .manifests import OdpmJsonReader, UserSettingsReader
from .types import OdpmJson, UserSettingsJson

if TYPE_CHECKING:
    from .config import Config


class ConfigLoader:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._deprecated = DeprecatedConfigHandler(config)
        self._defaults = ConfigDefaultsFactory(config)
        self._user_settings_reader = UserSettingsReader(
            config,
            create_default_user_settings=self._defaults.create_default_user_setting_json_content,
        )
        self._odpm_json_reader = OdpmJsonReader(
            config,
            rewrite_odpm_json=self.rewrite_odpm_json,
        )

    def check_for_config(self) -> None:
        self._deprecated.check_for_config()

    def get_project_odpm_json(self) -> None:
        self._odpm_json_reader.get_project_odpm_json()

    def rewrite_odpm_json(self) -> None:
        default_odpm_json_content = self._defaults.create_default_odpm_json_content()
        pathlib.Path(self.config.developing_project.project_path).mkdir(
            parents=True, exist_ok=True
        )
        with open(self.config.repo_odpm_json, "w", encoding="utf-8") as odpm_json_file:
            json.dump(
                default_odpm_json_content, odpm_json_file, ensure_ascii=False, indent=4
            )

    def get_user_settings_json(self) -> None:
        self._user_settings_reader.get_user_settings_json()

    def get_user_settings(self) -> None:
        self._user_settings_reader.get_user_settings()

    def get_odpm_settings(self) -> None:
        self._odpm_json_reader.get_odpm_settings()

    def check_file_for_deprecated_words(self, file_path: str) -> None:
        self._deprecated.check_file_for_deprecated_words(file_path)

    def beautify_module_list(self, modules) -> str:
        if not modules:
            return constants.DEFAULT_LIST_OF_MODULES
        if isinstance(modules, list):
            modules = ",".join(modules)
        if isinstance(modules, str):
            modules = modules.split(",")
            modules = [module.strip() for module in modules]
            modules = ",".join(modules)
        return modules

    def get_effective_odoo_build_date(self) -> str:
        cli_date = getattr(self.config.arguments, "odoo_build_date", None)
        if cli_date:
            return cli_date.strip()
        return (self.config._raw_odpm_json.get("odoo_build_date") or "").strip()

    def get_developing_project_link(self) -> str:
        return self._defaults.get_developing_project_link()

    def create_default_user_setting_json_content(self) -> UserSettingsJson:
        return self._defaults.create_default_user_setting_json_content()

    def create_default_odpm_json_content(self) -> OdpmJson:
        return self._defaults.create_default_odpm_json_content()
