from __future__ import annotations

import json
import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from .. import constants, translations
from ..errors import ConfigError
from ..interactive import prompt_input, stdin_is_interactive
from ..git import (
    FILE_SYSTEM_MARKER,
    GIT_MARKER,
    HTTP_MARKER,
    SSH_MARKER,
)
from ..inside_docker_app.logger import get_module_logger
from .types import DbCreationData, OdpmJson, UserSettingsJson

if TYPE_CHECKING:
    from .config import Config

_logger = get_module_logger(__name__)


class ConfigLoader:
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
            self.rewrite_odpm_json()

    def rewrite_odpm_json(self) -> None:
        default_odpm_json_content = self.create_default_odpm_json_content()
        pathlib.Path(self.config.developing_project.project_path).mkdir(
            parents=True, exist_ok=True
        )
        with open(self.config.repo_odpm_json, "w", encoding="utf-8") as odpm_json_file:
            json.dump(
                default_odpm_json_content, odpm_json_file, ensure_ascii=False, indent=4
            )

    def get_user_settings_json(self) -> None:
        self.config.user_settings_json = os.path.join(
            self.config.project_dir, constants.USER_CONFIG_FILE_NAME
        )
        if not os.path.exists(self.config.user_settings_json):
            default_user_settings_json_content = (
                self.create_default_user_setting_json_content()
            )
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
            self.rewrite_odpm_json()
        with open(self.config.repo_odpm_json) as repo_odpm_json:
            self.config._raw_odpm_json = json.load(repo_odpm_json)

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

    def _odoo_build_date_for_odpm_json(self, fallback: str) -> str:
        cli_date = getattr(self.config.arguments, "odoo_build_date", None)
        if cli_date:
            return cli_date.strip()
        return fallback

    def get_developing_project_link(self) -> str:
        config_json_dev_link = self.config.config_json_content.get("developing_project")
        if config_json_dev_link:
            return config_json_dev_link
        pd_manger_init_dev_link = self.config.pd_manager.init
        if pd_manger_init_dev_link == ".":
            pd_manger_init_dev_link = (
                f"file://{self.config.pd_manager.project_path}/my_odoo_project"
            )
            return pd_manger_init_dev_link
        for marker in [HTTP_MARKER, GIT_MARKER, SSH_MARKER, FILE_SYSTEM_MARKER]:
            if marker in pd_manger_init_dev_link:
                return pd_manger_init_dev_link
        pd_manger_init_dev_link = f"file://{os.path.join(self.config.pd_manager.project_path, pd_manger_init_dev_link)}"
        return pd_manger_init_dev_link

    def create_default_user_setting_json_content(self) -> UserSettingsJson:
        user_settings_content = UserSettingsJson(
            init_modules=self.config.config_json_content.get(
                "init_modules", constants.DEFAULT_INIT_MODULES
            ),
            update_modules=self.config.config_json_content.get(
                "update_modules", constants.DEFAULT_UPDATE_MODULES
            ),
            db_creation_data=DbCreationData(
                db_lang=self.config.config_json_content.get("db_creation_data", {}).get(
                    "db_lang", constants.DEFAULT_DB_CREATION_DATA_DB_LANG
                ),
                db_country_code=self.config.config_json_content.get(
                    "db_creation_data", {}
                ).get(
                    "db_country_code",
                    constants.DEFAULT_DB_CREATION_DATA_DB_COUNTRY_CODE,
                ),
                create_demo=self.config.config_json_content.get("db_creation_data", {}).get(
                    "create_demo", constants.DEFAULT_DB_CREATION_DATA_CREATE_DEMO
                ),
                db_default_admin_login=self.config.config_json_content.get(
                    "db_creation_data", {}
                ).get(
                    "db_default_admin_login",
                    constants.DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_LOGIN,
                ),
                db_default_admin_password=self.config.config_json_content.get(
                    "db_creation_data", {}
                ).get(
                    "db_default_admin_password",
                    constants.DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_PASSWORD,
                ),
            ),
            update_git_repos=self.config.config_json_content.get(
                "update_git_repos", constants.DEFAULT_UPDATE_GIT_REPOS
            ),
            clean_git_repos=self.config.config_json_content.get(
                "clean_git_repos", constants.DEFAULT_CLEAN_GIT_REPOS
            ),
            check_system=self.config.config_json_content.get(
                "check_system", constants.DEFAULT_CHECK_SYSTEM
            ),
            db_manager_password=self.config.config_json_content.get(
                "db_manager_password", constants.DEFAULT_DB_MANAGER_PASSWORD
            ),
            dev_mode=self.config.config_json_content.get(
                "dev_mode", constants.DEFAULT_DEV_MODE
            ),
            developing_project=self.get_developing_project_link(),
            pre_commit_map_files=self.config.config_json_content.get(
                "pre_commit_map_files", constants.DEFAULT_PRE_COMMIT_MAP_FILES
            ),
            sql_queries=self.config.config_json_content.get(
                "sql_queries", constants.DEFAULT_SQL_QUERIES
            ),
            use_oca_dependencies=self.config.config_json_content.get(
                "use_oca_dependencies", constants.DEFAULT_USE_OCA_DEPENDENCIES
            ),
            create_module_links=self.config.config_json_content.get(
                "create_module_links", constants.DEFAULT_CREATE_MODULE_LINKS
            ),
        )
        return user_settings_content

    def create_default_odpm_json_content(self) -> OdpmJson:
        if self.config.config_json_content:
            return OdpmJson(
                python_version=self.config.config_json_content.get(
                    "python_version",
                    self.config.arguments.python_version or constants.DEFAULT_PYTHON_VERSION,
                ),
                distro_name=self.config.config_json_content.get(
                    "distro_name",
                    self.config.arguments.distro_name or constants.DEFAULT_DISTRO_NAME,
                ),
                distro_version=self.config.config_json_content.get(
                    "distro_version",
                    self.config.arguments.distro_version or constants.DEFAULT_DISTRO_VERSION,
                ),
                postgres_version=self.config.config_json_content.get(
                    "postgres_version",
                    self.config.arguments.postgres_version
                    or constants.DEFAULT_POSTGRES_VERSION,
                ),
                odoo_version=self.config.config_json_content.get(
                    "odoo_version",
                    self.config.arguments.odoo_version or constants.ODOO_LATEST_VERSION,
                ),
                dependencies=self.config.config_json_content.get("dependencies", []),
                requirements_txt=self.config.config_json_content.get(
                    "requirements_txt", self.config.arguments.requirements_txt.split(",") or []
                ),
                odoo_build_date=self._odoo_build_date_for_odpm_json(
                    self.config.config_json_content.get(
                        "odoo_build_date", constants.ODOO_DEFAULT_BUILD_DATE
                    )
                ),
                odoo_git_link=self.config.config_json_content.get(
                    "odoo_git_link",
                    self.config.arguments.odoo_git_link or constants.ODOO_GIT_LINK,
                ),
                platform_name=self.config.config_json_content.get(
                    "platform_name",
                    self.config.arguments.platform_name or constants.PLATFORM_NAME,
                ),
                odpm_version=self.config._raw_odpm_json.get(
                    "odpm_version", constants.ODPM_VERSION
                ),
            )
        available_versions = [
            int(float(version)) for version in constants.ODOO_VERSION_DEFAULT_ENV
        ]
        available_versions_str = ", ".join(
            [str(float(version)) for version in available_versions]
        )
        user_odoo_version = self.config.arguments.odoo_version
        if not user_odoo_version:
            if not stdin_is_interactive():
                message = translations.get_translation(
                    translations.NON_INTERACTIVE_ODOO_VERSION_REQUIRED
                )
                _logger.error(message)
                raise ConfigError(message)
            while True:
                user_odoo_version = prompt_input(
                    translations.get_translation(translations.SET_ODOO_VERSION).format(
                        ODOO_LATEST_VERSION=constants.ODOO_LATEST_VERSION,
                        AVAILABEL_ODOO_VERSIONS_ARE=available_versions_str,
                    )
                )
                try:
                    if not user_odoo_version:
                        user_odoo_version = constants.ODOO_LATEST_VERSION
                    float_version_from_user = float(user_odoo_version)
                    if str(float_version_from_user) not in available_versions_str:
                        continue
                    user_odoo_version = str(float_version_from_user)
                    break
                except Exception:
                    continue

        _logger.info(
            translations.get_translation(translations.YOU_SELECT_ODOO_VERSION).format(
                SELECTED_ODOO_VERSION=user_odoo_version,
            )
        )
        default_odpm_json_content = OdpmJson(
            python_version=self.config._raw_odpm_json.get(
                "python_version",
                self.config.arguments.python_version
                or constants.ODOO_VERSION_DEFAULT_ENV[user_odoo_version][
                    "python_version"
                ],
            ),
            distro_version=self.config._raw_odpm_json.get(
                "distro_version",
                self.config.arguments.distro_version
                or constants.ODOO_VERSION_DEFAULT_ENV[user_odoo_version][
                    "distro_version"
                ],
            ),
            distro_name=self.config._raw_odpm_json.get(
                "distro_name",
                self.config.arguments.distro_name
                or constants.ODOO_VERSION_DEFAULT_ENV[user_odoo_version]["distro_name"],
            ),
            postgres_version=self.config._raw_odpm_json.get(
                "postgres_version",
                self.config.arguments.postgres_version or constants.DEFAULT_POSTGRES_VERSION,
            ),
            odoo_version=user_odoo_version,
            dependencies=self.config._raw_odpm_json.get("dependencies", []),
            requirements_txt=self.config._raw_odpm_json.get(
                "requirements_txt", self.config.arguments.requirements_txt.split(",") or []
            ),
            odoo_build_date=self._odoo_build_date_for_odpm_json(
                self.config._raw_odpm_json.get("odoo_build_date", constants.ODOO_DEFAULT_BUILD_DATE)
            ),
            odoo_git_link=self.config._raw_odpm_json.get(
                "odoo_git_link",
                self.config.arguments.odoo_git_link or constants.ODOO_GIT_LINK,
            ),
            platform_name=self.config._raw_odpm_json.get(
                "platform_name",
                self.config.arguments.platform_name or constants.PLATFORM_NAME,
            ),
            odpm_version=self.config._raw_odpm_json.get(
                "odpm_version", constants.ODPM_VERSION
            ),
        )
        return default_odpm_json_content
