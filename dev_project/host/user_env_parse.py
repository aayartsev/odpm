"""Parse and write host ``.env`` files (non-interactive paths)."""

from __future__ import annotations

import os
import platform
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from .. import constants
from ..debugger.constants import (
    ODPM_DEBUGGER_BACKEND_ENV,
    ODPM_DEBUGGER_CONNECT_HOST_ENV,
    ODPM_DEBUGGER_SUSPEND_ENV,
    ODPM_IDE_ENV,
)
from ..debugger.env_parsing import (
    parse_debugger_backend,
    parse_debugger_connect_host,
    parse_debugger_suspend,
    parse_odpm_ide,
)
from .postgres_service_name import parse_postgres_service_name
from ..compose.service_names import resolve_compose_naming
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..translations import _, parse_odpm_locale_setting

_logger = get_module_logger(__name__)


class _EnvDataRequired(TypedDict):
    BACKUP_DIR: str
    ODOO_PROJECTS_DIR: str
    PATH_TO_SSH_KEY: str
    ODOO_PORT: int
    POSTGRES_PORT: int
    DEBUGGER_PORT: int
    GEVENT_PORT: int
    ODPM_SCENARIO: str


class EnvData(_EnvDataRequired, total=False):
    ODPM_LOCALE: str
    ODPM_DEBUGGER_BACKEND: str
    ODPM_IDE: str
    ODPM_DEBUGGER_CONNECT_HOST: str
    ODPM_DEBUGGER_SUSPEND: str
    POSTGRES_SERVICE_NAME: str
    ODPM_COMPOSE_PREFIX: str


@dataclass(frozen=True)
class ParsedUserEnv:
    dotenv: dict[str, str]
    backups: str
    odoo_projects_dir: str
    debugger_port: int
    odoo_port: int
    postgres_port: int
    postgres_service_name: str
    gevent_port: int
    path_to_ssh_key: str
    odpm_scenario: str
    odpm_locale: str | None
    debugger_backend: str
    odpm_ide: str
    debugger_connect_host: str
    debugger_suspend: bool
    compose_prefix: str | None
    compose_project_name: str | None
    odoo_service_name: str
    postgres_volume_name: str


def resolve_env_file_path(
    pd_manager: ProjectDirManager, *, config_home_dir: str
) -> str:
    """Return project-local .env when present, else the home config path."""
    project_env_file = os.path.join(
        pd_manager.project_path, constants.ENV_FILE_NAME
    )
    if os.path.exists(project_env_file):
        return project_env_file
    return os.path.join(config_home_dir, constants.ENV_FILE_NAME)


def load_dotenv_dict(env_file: str) -> dict[str, str]:
    parser = ConfigParser()
    parser.optionxform = str
    with open(env_file) as stream:
        parser.read_string("[env]\n" + stream.read())
    return {key: str(value) for key, value in parser["env"].items()}


def parse_dotenv_dict(env_dict: dict[str, str]) -> ParsedUserEnv:
    raw_scenario = env_dict.get("ODPM_SCENARIO", constants.DEFAULT_ODPM_SCENARIO)
    if raw_scenario not in constants.ODPM_SCENARIO_VALUES:
        _logger.warning(
            _("Unknown ODPM_SCENARIO=%r, using %s"),
            raw_scenario,
            constants.DEFAULT_ODPM_SCENARIO,
        )
        raw_scenario = constants.DEFAULT_ODPM_SCENARIO
    path_to_ssh_key = env_dict.get("PATH_TO_SSH_KEY", "")
    if isinstance(path_to_ssh_key, str) and platform.system() == "Windows":
        path_to_ssh_key = path_to_ssh_key.replace("\\", "\\\\")
    raw_locale = env_dict.get(constants.ODPM_LOCALE_ENV_KEY, "").strip()
    odpm_locale: str | None
    if raw_locale:
        parsed_locale = parse_odpm_locale_setting(raw_locale)
        if parsed_locale is None:
            _logger.warning(
                _("Invalid %s=%r, falling back to system locale"),
                constants.ODPM_LOCALE_ENV_KEY,
                raw_locale,
            )
            odpm_locale = None
        else:
            odpm_locale = parsed_locale
    else:
        odpm_locale = None
    naming = resolve_compose_naming(
        compose_prefix_raw=env_dict.get(constants.ODPM_COMPOSE_PREFIX_ENV),
        legacy_postgres_service_name=parse_postgres_service_name(
            env_dict.get(constants.POSTGRES_SERVICE_NAME_ENV)
        ),
    )
    return ParsedUserEnv(
        dotenv=dict(env_dict),
        backups=env_dict["BACKUP_DIR"],
        odoo_projects_dir=env_dict["ODOO_PROJECTS_DIR"],
        debugger_port=int(
            env_dict.get("DEBUGGER_PORT", str(constants.DEBUGGER_DEFAULT_PORT))
        ),
        odoo_port=int(env_dict.get("ODOO_PORT", str(constants.ODOO_DEFAULT_PORT))),
        postgres_port=int(
            env_dict.get("POSTGRES_PORT", str(constants.POSTGRES_DEFAULT_PORT))
        ),
        postgres_service_name=naming.postgres_service_name,
        gevent_port=int(
            env_dict.get("GEVENT_PORT", str(constants.GEVENT_DEFAULT_PORT))
        ),
        path_to_ssh_key=path_to_ssh_key,
        odpm_scenario=raw_scenario,
        odpm_locale=odpm_locale,
        debugger_backend=parse_debugger_backend(
            env_dict.get(ODPM_DEBUGGER_BACKEND_ENV)
        ),
        odpm_ide=parse_odpm_ide(env_dict.get(ODPM_IDE_ENV)),
        debugger_connect_host=parse_debugger_connect_host(
            env_dict.get(ODPM_DEBUGGER_CONNECT_HOST_ENV)
        ),
        debugger_suspend=parse_debugger_suspend(
            env_dict.get(ODPM_DEBUGGER_SUSPEND_ENV)
        ),
        compose_prefix=naming.compose_prefix,
        compose_project_name=naming.compose_project_name,
        odoo_service_name=naming.odoo_service_name,
        postgres_volume_name=naming.postgres_volume_name,
    )


def write_env_file(local_env_file: str, new_env_data: EnvData) -> None:
    with open(local_env_file, "w", encoding="utf-8") as env_file:
        for key_name, value in new_env_data.items():
            if key_name == constants.ODPM_LOCALE_ENV_KEY and not str(value).strip():
                continue
            env_file.write(f"{key_name}={value}\n")


def has_noninteractive_env_configuration(pd_manager: ProjectDirManager) -> bool:
    if any(
        os.environ.get(key)
        for key in (
            "BACKUP_DIR",
            "ODOO_PROJECTS_DIR",
            "PATH_TO_SSH_KEY",
            "ODOO_PORT",
            "POSTGRES_PORT",
            "DEBUGGER_PORT",
            "GEVENT_PORT",
            "ODPM_SCENARIO",
            constants.ODPM_LOCALE_ENV_KEY,
            constants.ODPM_COMPOSE_PREFIX_ENV,
            ODPM_DEBUGGER_BACKEND_ENV,
            ODPM_IDE_ENV,
        )
    ):
        return True
    project_env = os.path.join(pd_manager.project_path, constants.ENV_FILE_NAME)
    return os.path.isfile(project_env)


def debugger_env_defaults_from_environ() -> EnvData:
    return EnvData(
        ODPM_DEBUGGER_BACKEND=parse_debugger_backend(
            os.environ.get(ODPM_DEBUGGER_BACKEND_ENV)
        ),
        ODPM_IDE=parse_odpm_ide(os.environ.get(ODPM_IDE_ENV)),
        ODPM_DEBUGGER_CONNECT_HOST=parse_debugger_connect_host(
            os.environ.get(ODPM_DEBUGGER_CONNECT_HOST_ENV)
        ),
        ODPM_DEBUGGER_SUSPEND="1"
        if parse_debugger_suspend(os.environ.get(ODPM_DEBUGGER_SUSPEND_ENV))
        else "0",
    )


def build_env_data_from_environ_or_defaults() -> EnvData:
    default_odoo_projects_src_dir = os.path.join(Path.home(), "odoo_projects")
    default_backup_dir = os.path.join(Path.home(), "odoo_backups")
    raw_scenario = os.environ.get("ODPM_SCENARIO", constants.DEFAULT_ODPM_SCENARIO)
    if raw_scenario not in constants.ODPM_SCENARIO_VALUES:
        raw_scenario = constants.DEFAULT_ODPM_SCENARIO
    env_data = EnvData(
        BACKUP_DIR=os.environ.get("BACKUP_DIR", default_backup_dir),
        ODOO_PROJECTS_DIR=os.environ.get(
            "ODOO_PROJECTS_DIR", default_odoo_projects_src_dir
        ),
        PATH_TO_SSH_KEY=os.environ.get("PATH_TO_SSH_KEY", ""),
        ODOO_PORT=int(
            os.environ.get("ODOO_PORT", str(constants.ODOO_DEFAULT_PORT))
        ),
        POSTGRES_PORT=int(
            os.environ.get("POSTGRES_PORT", str(constants.POSTGRES_DEFAULT_PORT))
        ),
        DEBUGGER_PORT=int(
            os.environ.get("DEBUGGER_PORT", str(constants.DEBUGGER_DEFAULT_PORT))
        ),
        GEVENT_PORT=int(
            os.environ.get("GEVENT_PORT", str(constants.GEVENT_DEFAULT_PORT))
        ),
        ODPM_SCENARIO=raw_scenario,
    )
    locale_value = os.environ.get(constants.ODPM_LOCALE_ENV_KEY, "").strip()
    if locale_value:
        env_data[constants.ODPM_LOCALE_ENV_KEY] = locale_value
    env_data.update(debugger_env_defaults_from_environ())
    raw_postgres_service = os.environ.get(
        constants.POSTGRES_SERVICE_NAME_ENV, ""
    ).strip()
    if raw_postgres_service:
        env_data[constants.POSTGRES_SERVICE_NAME_ENV] = parse_postgres_service_name(
            raw_postgres_service
        )
    raw_compose_prefix = os.environ.get(constants.ODPM_COMPOSE_PREFIX_ENV, "").strip()
    if raw_compose_prefix:
        env_data[constants.ODPM_COMPOSE_PREFIX_ENV] = raw_compose_prefix
    return env_data
