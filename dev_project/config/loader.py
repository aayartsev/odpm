from __future__ import annotations

import json
import os
import pathlib
from typing import TYPE_CHECKING

from .. import constants, translations
from ..logging import get_module_logger
from .defaults import ConfigDefaultsFactory
from .manifests import OdpmJsonReader, UserSettingsReader
from .types import OdpmJson, UserSettingsJson

if TYPE_CHECKING:
    from .config import Config

_logger = get_module_logger(__name__)


class ConfigLoader:
    def __init__(self, config: Config) -> None:
        self.config = config
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
