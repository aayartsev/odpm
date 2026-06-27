"""Host user ``.env`` bootstrap: parse, wizard, and ``CreateUserEnvironment`` facade."""

from __future__ import annotations

import os
import sys

from .. import constants
from ..debugger.constants import (
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
    DEFAULT_DEBUGGER_BACKEND,
    DEFAULT_DEBUGGER_CONNECT_HOST,
    DEFAULT_ODPM_IDE,
)
from ..errors import ConfigError
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager
from ..translations import _, apply_locale_from_sources
from . import user_env_parse as parse
from . import user_env_wizard as wizard
from .user_env_parse import EnvData, ParsedUserEnv

_logger = get_module_logger(__name__)

__all__ = ["CreateUserEnvironment", "EnvData", "ParsedUserEnv"]


def _stdin_is_interactive() -> bool:
    from ..interactive import stdin_is_interactive

    return stdin_is_interactive()


def _apply_parsed_user_env(target: CreateUserEnvironment, parsed: ParsedUserEnv) -> None:
    target._project_dotenv = parsed.dotenv
    target.backups = parsed.backups
    target.odoo_projects_dir = parsed.odoo_projects_dir
    target.debugger_port = parsed.debugger_port
    target.odoo_port = parsed.odoo_port
    target.postgres_port = parsed.postgres_port
    target.postgres_service_name = parsed.postgres_service_name
    target.gevent_port = parsed.gevent_port
    target.path_to_ssh_key = parsed.path_to_ssh_key
    target.odpm_scenario = parsed.odpm_scenario
    target.odpm_locale = parsed.odpm_locale
    target.debugger_backend = parsed.debugger_backend
    target.odpm_ide = parsed.odpm_ide
    target.debugger_connect_host = parsed.debugger_connect_host
    target.debugger_suspend = parsed.debugger_suspend
    target.compose_prefix = parsed.compose_prefix
    target.compose_project_name = parsed.compose_project_name
    target.odoo_service_name = parsed.odoo_service_name
    target.postgres_volume_name = parsed.postgres_volume_name
    target.compose_network_logical = parsed.compose_network_logical
    target.compose_network_external = parsed.compose_network_external
    target.compose_network_physical = parsed.compose_network_physical


class CreateUserEnvironment:
    def __init__(self, pd_manager: ProjectDirManager):
        self.pd_manager = pd_manager
        self.config_home_dir = self.pd_manager.home_config_dir
        self.env_file = self.get_env_file_path()
        self.odpm_locale: str | None = None
        self.parse_env_file()
        apply_locale_from_sources(self.odpm_locale)

    def resolve_env_file_path(self) -> str:
        return parse.resolve_env_file_path(
            self.pd_manager, config_home_dir=self.config_home_dir
        )

    def ensure_default_env_file(self, env_path: str) -> None:
        """Create *env_path* via wizard or non-interactive defaults when missing."""
        if os.path.exists(env_path):
            return
        parent_dir = os.path.dirname(env_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if sys.modules[__name__]._stdin_is_interactive():
            self.create_env_file(env_path)
        else:
            self.create_env_file_noninteractive(env_path)

    def get_env_file_path(self) -> str:
        if not os.path.exists(self.config_home_dir):
            os.makedirs(self.config_home_dir)
        env_path = self.resolve_env_file_path()
        self.ensure_default_env_file(env_path)
        return env_path

    def project_dotenv_dict(self) -> dict[str, str]:
        """Return effective merged home + project ``.env`` for manifest ``${VAR}`` lookup."""
        return dict(self._project_dotenv)

    def parse_env_file(self) -> None:
        env_dict = parse.load_layered_dotenv_dict(
            project_path=self.pd_manager.project_path,
            config_home_dir=self.config_home_dir,
        )
        _apply_parsed_user_env(self, parse.parse_dotenv_dict(env_dict))

    def create_env_file(self, local_env_file: str) -> None:
        new_env_data = self._build_env_data_interactive()
        parse.write_env_file(local_env_file, new_env_data)

    def create_env_file_noninteractive(self, local_env_file: str) -> None:
        if not parse.has_noninteractive_env_configuration(self.pd_manager):
            message = _(
                "Non-interactive mode requires an existing .env file in the project "
                "directory or under ~/.odpm/.env. Create it manually or set "
                "environment variables (BACKUP_DIR, ODOO_PROJECTS_DIR, "
                "PATH_TO_SSH_KEY, ODOO_PORT, POSTGRES_PORT, DEBUGGER_PORT, "
                "GEVENT_PORT, ODPM_SCENARIO, ODPM_LOCALE, ODPM_DEBUGGER_BACKEND, "
                "ODPM_IDE) before the first run."
            )
            _logger.error(message)
            raise ConfigError(message)
        new_env_data = parse.build_env_data_from_environ_or_defaults()
        parse.write_env_file(local_env_file, new_env_data)
        _logger.info(
            _(
                "Created {ENV_FILE} from environment variables and defaults "
                "(non-interactive mode)."
            ).format(
                ENV_FILE=local_env_file,
            )
        )

    def _build_env_data_interactive(self) -> EnvData:
        env_data = EnvData(
            BACKUP_DIR=self.get_from_user_backup_dir(),
            ODOO_PROJECTS_DIR=self.get_from_user_odoo_projects_src_dir(),
            PATH_TO_SSH_KEY="",
            ODOO_PORT=self.get_from_user_odoo_port(),
            POSTGRES_PORT=self.get_from_user_postgres_port(),
            DEBUGGER_PORT=self.get_from_user_debugger_port(),
            GEVENT_PORT=self.get_from_user_gevent_port(),
            ODPM_SCENARIO=self.get_from_user_odpm_scenario(),
        )
        env_data.update(
            self._debugger_env_data_interactive(
                odpm_scenario=env_data["ODPM_SCENARIO"]
            )
        )
        locale_value = self.get_from_user_odpm_locale()
        if locale_value:
            env_data[constants.ODPM_LOCALE_ENV_KEY] = locale_value
        return env_data

    def _debugger_env_data_interactive(self, *, odpm_scenario: str) -> EnvData:
        defaults = EnvData(
            ODPM_DEBUGGER_BACKEND=DEFAULT_DEBUGGER_BACKEND,
            ODPM_IDE=DEFAULT_ODPM_IDE,
            ODPM_DEBUGGER_CONNECT_HOST=DEFAULT_DEBUGGER_CONNECT_HOST,
            ODPM_DEBUGGER_SUSPEND="0",
        )
        if odpm_scenario != constants.DEVELOPER_SCENARIO:
            return defaults
        debugger_backend = self.get_from_user_debugger_backend()
        odpm_ide = self.get_from_user_odpm_ide()
        connect_host = DEFAULT_DEBUGGER_CONNECT_HOST
        suspend = "0"
        if debugger_backend == DEBUGGER_BACKEND_PYDEVD_CONNECT:
            connect_host = self.get_from_user_debugger_connect_host()
            suspend = "1" if self.get_from_user_debugger_suspend() else "0"
        return EnvData(
            ODPM_DEBUGGER_BACKEND=debugger_backend,
            ODPM_IDE=odpm_ide,
            ODPM_DEBUGGER_CONNECT_HOST=connect_host,
            ODPM_DEBUGGER_SUSPEND=suspend,
        )

    def get_from_user_odoo_projects_src_dir(self) -> str:
        return wizard.get_from_user_odoo_projects_src_dir()

    def get_from_user_backup_dir(self) -> str:
        return wizard.get_from_user_backup_dir()

    def get_from_user_odoo_port(self) -> int:
        return wizard.get_from_user_odoo_port()

    def get_from_user_postgres_port(self) -> int:
        return wizard.get_from_user_postgres_port()

    def get_from_user_debugger_port(self) -> int:
        return wizard.get_from_user_debugger_port()

    def get_from_user_gevent_port(self) -> int:
        return wizard.get_from_user_gevent_port()

    def get_from_user_odpm_scenario(self) -> str:
        return wizard.get_from_user_odpm_scenario()

    def get_from_user_odpm_locale(self) -> str:
        return wizard.get_from_user_odpm_locale()

    def get_from_user_debugger_connect_host(self) -> str:
        return wizard.get_from_user_debugger_connect_host()

    def get_from_user_debugger_suspend(self) -> bool:
        return wizard.get_from_user_debugger_suspend()

    def get_from_user_debugger_backend(self) -> str:
        return wizard.get_from_user_debugger_backend()

    def get_from_user_odpm_ide(self) -> str:
        return wizard.get_from_user_odpm_ide()
