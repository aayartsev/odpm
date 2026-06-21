"""Default manifest content factories and interactive bootstrap prompts."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from ... import constants
from ...translations import _
from ...errors import ConfigError
from ...interactive import prompt_input, stdin_is_interactive
from ...git import (
    FILE_SYSTEM_MARKER,
    GIT_MARKER,
    HTTP_MARKER,
    SSH_MARKER,
)
from ...logging import get_module_logger
from ..types import DbCreationData, OdpmJson, UserSettingsJson

if TYPE_CHECKING:
    from ..config import Config

_logger = get_module_logger(__name__)


class ConfigDefaultsFactory:
    def __init__(self, config: Config) -> None:
        self.config = config

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

    def _default_manifest_database_block(self) -> dict[str, Any]:
        legacy = self.config.config_json_content.get("db_creation_data") or {}
        db_block = self.config.config_json_content.get("database")
        if not isinstance(db_block, dict):
            db_block = {}
        language = db_block.get("language") or legacy.get(
            "db_lang", constants.DEFAULT_DB_CREATION_DATA_DB_LANG
        )
        if "country" in db_block:
            country = db_block["country"]
        elif "db_country_code" in legacy:
            country = legacy["db_country_code"]
        else:
            country = constants.DEFAULT_DB_CREATION_DATA_DB_COUNTRY_CODE
        block: dict[str, Any] = {"language": str(language)}
        if country is not None or "country" in db_block or "db_country_code" in legacy:
            block["country"] = country
        return block

    def create_default_user_setting_json_content(self) -> UserSettingsJson:
        user_settings_content = UserSettingsJson(
            init_modules=self.config.config_json_content.get(
                "init_modules", constants.DEFAULT_INIT_MODULES
            ),
            update_modules=self.config.config_json_content.get(
                "update_modules", constants.DEFAULT_UPDATE_MODULES
            ),
            db_creation_data=DbCreationData(
                db_lang=constants.DEFAULT_DB_CREATION_DATA_DB_LANG,
                db_country_code=constants.DEFAULT_DB_CREATION_DATA_DB_COUNTRY_CODE,
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

    def _odoo_build_date_for_odpm_json(self, fallback: str) -> str:
        cli_date = getattr(self.config.arguments, "odoo_build_date", None)
        if cli_date:
            return cli_date.strip()
        return fallback

    def _resolve_odoo_version_for_default_manifest(self) -> str:
        user_odoo_version = self.config.arguments.odoo_version
        if user_odoo_version:
            return user_odoo_version

        if not stdin_is_interactive():
            message = _("Non-interactive mode requires odoo_version in the developing project's odpm.json or pass --odoo-version on the command line.")
            _logger.error(message)
            raise ConfigError(message)

        available_versions = [
            int(float(version)) for version in constants.ODOO_VERSION_DEFAULT_ENV
        ]
        available_versions_str = ", ".join(
            [str(float(version)) for version in available_versions]
        )
        while True:
            user_odoo_version = prompt_input(
                _("Please, enter odoo versions of this project. There is list of supported versions: {AVAILABEL_ODOO_VERSIONS_ARE}. You can leave default {ODOO_LATEST_VERSION} or write your own. Press 'Enter' to leave default value:\n").format(
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
            _('You select this odoo version: {SELECTED_ODOO_VERSION}\n').format(
                SELECTED_ODOO_VERSION=user_odoo_version,
            )
        )
        return user_odoo_version

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
                    "odpm_version", constants.MANIFEST_V1_CONTRACT_LINE
                ),
            )

        user_odoo_version = self._resolve_odoo_version_for_default_manifest()
        return OdpmJson(
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
                "odpm_version", constants.MANIFEST_V1_CONTRACT_LINE
            ),
        )

    def create_default_odpm_json_write_payload(self) -> dict[str, Any]:
        payload = dict(self.create_default_odpm_json_content())
        payload["database"] = self._default_manifest_database_block()
        return payload
