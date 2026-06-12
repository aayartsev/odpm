import os
import platform
from configparser import ConfigParser
from pathlib import Path
from typing import TypedDict

from .. import constants
from ..debugger.backends import DEBUGGER_BACKENDS
from ..debugger.constants import (
    DEBUGGER_BACKEND_LABELS,
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
    DEFAULT_DEBUGGER_BACKEND,
    DEFAULT_DEBUGGER_CONNECT_HOST,
    DEFAULT_ODPM_IDE,
    ODPM_DEBUGGER_BACKEND_ENV,
    ODPM_DEBUGGER_CONNECT_HOST_ENV,
    ODPM_DEBUGGER_SUSPEND_ENV,
    ODPM_IDE_ENV,
    ODPM_IDE_LABELS,
    ODPM_IDE_VALUES,
)
from ..debugger.env_parsing import (
    parse_debugger_backend,
    parse_debugger_connect_host,
    parse_debugger_suspend,
    parse_odpm_ide,
)
from ..translations import _, apply_locale_from_sources, parse_odpm_locale_setting
from ..errors import ConfigError
from ..interactive import prompt_input, stdin_is_interactive
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager

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


class CreateUserEnvironment:
    def __init__(self, pd_manager: ProjectDirManager):
        self.pd_manager = pd_manager
        self.config_home_dir = self.pd_manager.home_config_dir
        self.env_file = self.get_env_file_path()
        self.odpm_locale: str | None = None
        self.parse_env_file()
        apply_locale_from_sources(self.odpm_locale)

    def resolve_env_file_path(self) -> str:
        """Return project-local .env when present, else the home config path."""
        project_env_file = os.path.join(
            self.pd_manager.project_path, constants.ENV_FILE_NAME
        )
        if os.path.exists(project_env_file):
            return project_env_file
        return os.path.join(self.config_home_dir, constants.ENV_FILE_NAME)

    def ensure_default_env_file(self, env_path: str) -> None:
        """Create *env_path* via wizard or non-interactive defaults when missing."""
        if os.path.exists(env_path):
            return
        parent_dir = os.path.dirname(env_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if stdin_is_interactive():
            self.create_env_file(env_path)
        else:
            self.create_env_file_noninteractive(env_path)

    def get_env_file_path(self) -> str:
        if not os.path.exists(self.config_home_dir):
            os.makedirs(self.config_home_dir)
        env_path = self.resolve_env_file_path()
        self.ensure_default_env_file(env_path)
        return env_path

    def parse_env_file(self) -> None:
        parser = ConfigParser()
        with open(self.env_file) as stream:
            parser.read_string("[env]\n" + stream.read())
        self.backups = parser["env"]["BACKUP_DIR"]
        self.odoo_projects_dir = parser["env"]["ODOO_PROJECTS_DIR"]
        self.debugger_port = int(
            parser["env"].get("DEBUGGER_PORT", str(constants.DEBUGGER_DEFAULT_PORT))
        )
        self.odoo_port = int(
            parser["env"].get("ODOO_PORT", str(constants.ODOO_DEFAULT_PORT))
        )
        self.postgres_port = int(
            parser["env"].get("POSTGRES_PORT", str(constants.POSTGRES_DEFAULT_PORT))
        )
        self.gevent_port = int(
            parser["env"].get("GEVENT_PORT", str(constants.GEVENT_DEFAULT_PORT))
        )
        path_to_ssh_key = parser["env"].get("PATH_TO_SSH_KEY", "")
        raw_scenario = parser["env"].get(
            "ODPM_SCENARIO", constants.DEFAULT_ODPM_SCENARIO
        )
        if raw_scenario not in constants.ODPM_SCENARIO_VALUES:
            _logger.warning(
                "Unknown ODPM_SCENARIO=%r, using %s",
                raw_scenario,
                constants.DEFAULT_ODPM_SCENARIO,
            )
            raw_scenario = constants.DEFAULT_ODPM_SCENARIO
        self.odpm_scenario = raw_scenario
        if isinstance(path_to_ssh_key, str) and platform.system() == "Windows":
            path_to_ssh_key = path_to_ssh_key.replace("\\", "\\\\")
        self.path_to_ssh_key = path_to_ssh_key
        raw_locale = parser["env"].get(constants.ODPM_LOCALE_ENV_KEY, "").strip()
        if raw_locale:
            parsed_locale = parse_odpm_locale_setting(raw_locale)
            if parsed_locale is None:
                _logger.warning(
                    "Invalid %s=%r, falling back to system locale",
                    constants.ODPM_LOCALE_ENV_KEY,
                    raw_locale,
                )
                self.odpm_locale = None
            else:
                self.odpm_locale = parsed_locale
        else:
            self.odpm_locale = None
        self.debugger_backend = parse_debugger_backend(
            parser["env"].get(ODPM_DEBUGGER_BACKEND_ENV)
        )
        self.odpm_ide = parse_odpm_ide(parser["env"].get(ODPM_IDE_ENV))
        self.debugger_connect_host = parse_debugger_connect_host(
            parser["env"].get(ODPM_DEBUGGER_CONNECT_HOST_ENV)
        )
        self.debugger_suspend = parse_debugger_suspend(
            parser["env"].get(ODPM_DEBUGGER_SUSPEND_ENV)
        )

    def create_env_file(self, local_env_file: str) -> None:
        new_env_data = self._build_env_data_interactive()
        self._write_env_file(local_env_file, new_env_data)

    def create_env_file_noninteractive(self, local_env_file: str) -> None:
        if not self._has_noninteractive_env_configuration():
            message = _(
                "Non-interactive mode requires an existing .env file in the project directory "
                "or under ~/.odpm/.env. Create it manually or set environment variables "
                "(BACKUP_DIR, ODOO_PROJECTS_DIR, PATH_TO_SSH_KEY, ODOO_PORT, POSTGRES_PORT, "
                "DEBUGGER_PORT, GEVENT_PORT, ODPM_SCENARIO, ODPM_LOCALE, "
                "ODPM_DEBUGGER_BACKEND, ODPM_IDE) before the first run."
            )
            _logger.error(message)
            raise ConfigError(message)
        new_env_data = self._build_env_data_from_environ_or_defaults()
        self._write_env_file(local_env_file, new_env_data)
        _logger.info(
            _('Created {ENV_FILE} from environment variables and defaults (non-interactive mode).').format(
                ENV_FILE=local_env_file,
            )
        )

    def _write_env_file(self, local_env_file: str, new_env_data: EnvData) -> None:
        with open(local_env_file, "w", encoding="utf-8") as env_file:
            for key_name, value in new_env_data.items():
                if key_name == constants.ODPM_LOCALE_ENV_KEY and not str(value).strip():
                    continue
                env_file.write(f"{key_name}={value}\n")

    def _has_noninteractive_env_configuration(self) -> bool:
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
                ODPM_DEBUGGER_BACKEND_ENV,
                ODPM_IDE_ENV,
            )
        ):
            return True
        project_env = os.path.join(
            self.pd_manager.project_path, constants.ENV_FILE_NAME
        )
        return os.path.isfile(project_env)

    def _build_env_data_from_environ_or_defaults(self) -> EnvData:
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
        env_data.update(self._debugger_env_defaults_from_environ())
        return env_data

    def _debugger_env_defaults_from_environ(self) -> EnvData:
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
        default_odoo_projects_src_dir = os.path.join(Path.home(), "odoo_projects")
        user_dir = prompt_input(
            _("Set other odoo projects sources directory, You can leave default {DEFAULT_ODOO_PROJECTS_SRC_DIR} or write your own. Press 'Enter' to leave default value:").format(
                DEFAULT_ODOO_PROJECTS_SRC_DIR=default_odoo_projects_src_dir,
            )
        )
        if not user_dir:
            user_dir = default_odoo_projects_src_dir
        _logger.info(
            _('You select this other odoo projects sources dir: {SELECTED_ODOO_PROJECTS_DIR}\n').format(
                SELECTED_ODOO_PROJECTS_DIR=user_dir,
            )
        )
        return user_dir

    def get_from_user_backup_dir(self) -> str:
        default_backup_dir = os.path.join(Path.home(), "odoo_backups")
        user_dir = prompt_input(
            _("Set directory for odoo creating/restoring backups, You can leave default {DEFAULT_ODOO_BACKUP_DIR} or write your own. Press 'Enter' to leave default value:").format(
                DEFAULT_ODOO_BACKUP_DIR=default_backup_dir,
            )
        )
        if not user_dir:
            user_dir = default_backup_dir
        _logger.info(
            _('You select this odoo backups dir: {SELECTED_ODOO_BACKUPS_DIR}\n').format(
                SELECTED_ODOO_BACKUPS_DIR=user_dir,
            )
        )
        return user_dir

    def get_from_user_odoo_port(self) -> int:
        default_port = constants.ODOO_DEFAULT_PORT
        port = prompt_input(
            _("Set odoo port which it will listen. You can leave default {DEFAULT_ODOO_PORT} or write your own. Press 'Enter' to leave default value:\n").format(
                DEFAULT_ODOO_PORT=default_port,
            )
        )
        if not port:
            port = default_port
        _logger.info(
            _('You select this port for which odoo will listen: {SELECTED_ODOO_PORT}\n').format(
                SELECTED_ODOO_PORT=default_port,
            )
        )
        return int(port)

    def get_from_user_postgres_port(self) -> int:
        default_port = constants.POSTGRES_DEFAULT_PORT
        port = prompt_input(
            _("Set PostgreSQL database server port which it will listen. You can leave default {DEFAULT_POSTGRES_PORT} or write your own. Press 'Enter' to leave default value:\n").format(
                DEFAULT_POSTGRES_PORT=default_port,
            )
        )
        if not port:
            port = default_port
        _logger.info(
            _('You select this port for which PostgreSQL database server will listen: {SELECTED_POSTGRES_PORT}\n').format(
                SELECTED_POSTGRES_PORT=default_port,
            )
        )
        return int(port)

    def get_from_user_debugger_port(self) -> int:
        default_port = constants.DEBUGGER_DEFAULT_PORT
        port = prompt_input(
            _("Set debugger port which it will listen. You can leave default {DEFAULT_DEBUGGER_PORT} or write your own. Press 'Enter' to leave default value:\n").format(
                DEFAULT_DEBUGGER_PORT=default_port,
            )
        )
        if not port:
            port = default_port
        _logger.info(
            _('You select this port for which Python Debugger will listen: {SELECTED_DEBUGGER_PORT}\n').format(
                SELECTED_DEBUGGER_PORT=default_port,
            )
        )
        return int(port)

    def get_from_user_gevent_port(self) -> int:
        default_port = constants.GEVENT_DEFAULT_PORT
        port = prompt_input(
            _("Set gevent port which it will listen. You can leave default {DEFAULT_GEVENT_PORT} or write your own. Press 'Enter' to leave default value:\n").format(
                DEFAULT_GEVENT_PORT=default_port,
            )
        )
        if not port:
            port = default_port
        _logger.info(
            _('You select this port for which Odoo Gevent Websocket System will listen: {SELECTED_GEVENT_PORT}\n').format(
                SELECTED_GEVENT_PORT=default_port,
            )
        )
        return int(port)

    def get_from_user_odpm_scenario(self) -> str:
        default_odpm_scenario = constants.DEFAULT_ODPM_SCENARIO
        list_of_scenarios = "\n"
        for scenario in constants.ODPM_SCENARIOS.items():
            list_of_scenarios += f"{scenario[0]} - {scenario[1]}\n"
        odpm_scenario_key = prompt_input(
            _("Please select scenario by number of odpm usage from this list {LIST_OF_SCENARIOS}\n Press 'Enter' to leave default value:\n").format(
                LIST_OF_SCENARIOS=list_of_scenarios,
            )
        )

        if not odpm_scenario_key:
            selected_scenario = default_odpm_scenario
        else:
            odpm_scenario_key = int(odpm_scenario_key)
            selected_scenario = constants.ODPM_SCENARIOS.get(
                odpm_scenario_key, default_odpm_scenario
            )
        _logger.info(
            _('You select {SELECTED_ODPM_SCENARIO} scenario  for odpm usage\n').format(
                SELECTED_ODPM_SCENARIO=selected_scenario,
            )
        )
        return str(selected_scenario)

    def get_from_user_odpm_locale(self) -> str:
        from ..translations import _locale_from_environment

        system_locale = _locale_from_environment()
        user_locale = prompt_input(
            _(
                "Set odpm host message language. System locale is {SYSTEM_LOCALE}. "
                "Press 'Enter' to keep the system default or type a locale "
                "(for example ru_RU):"
            ).format(SYSTEM_LOCALE=system_locale)
        )
        if not user_locale:
            _logger.info(
                _(
                    "You selected the system default locale for odpm messages: {SELECTED_LOCALE}\n"
                ).format(SELECTED_LOCALE=system_locale)
            )
            return ""
        parsed_locale = parse_odpm_locale_setting(user_locale)
        if parsed_locale is None:
            _logger.warning(
                "Invalid %s=%r, using system locale %s",
                constants.ODPM_LOCALE_ENV_KEY,
                user_locale,
                system_locale,
            )
            return ""
        _logger.info(
            _(
                "You selected this locale for odpm messages: {SELECTED_LOCALE}\n"
            ).format(SELECTED_LOCALE=parsed_locale)
        )
        return parsed_locale

    def get_from_user_debugger_connect_host(self) -> str:
        default_host = DEFAULT_DEBUGGER_CONNECT_HOST
        user_host = prompt_input(
            _(
                "Set IDE host name for pydevd_connect (container connects to Debug Server). "
                "Press 'Enter' for default {DEFAULT_HOST}:\n"
            ).format(DEFAULT_HOST=default_host)
        )
        if not user_host:
            selected = default_host
        else:
            selected = parse_debugger_connect_host(user_host)
        _logger.info(
            _("You selected debugger connect host: {SELECTED_HOST}\n").format(
                SELECTED_HOST=selected,
            )
        )
        return selected

    def get_from_user_debugger_suspend(self) -> bool:
        choice = prompt_input(
            _(
                "Suspend Odoo until PyCharm Debug Server connects? "
                "Answer y/yes or n/no (Enter for no):\n"
            )
        )
        selected = parse_debugger_suspend(choice)
        _logger.info(
            _(
                "You selected debugger suspend on connect: {SELECTED_SUSPEND}\n"
            ).format(SELECTED_SUSPEND="yes" if selected else "no")
        )
        return selected

    def get_from_user_debugger_backend(self) -> str:
        default_backend = DEFAULT_DEBUGGER_BACKEND
        available_backends = sorted(DEBUGGER_BACKENDS)
        options = "\n".join(
            f"{index} - {DEBUGGER_BACKEND_LABELS.get(backend_id, backend_id)}"
            for index, backend_id in enumerate(available_backends, start=1)
        )
        choice = prompt_input(
            _(
                "Select debugger backend for developer scenario "
                "(Enter for default {DEFAULT_BACKEND}):\n{OPTIONS}\n"
            ).format(DEFAULT_BACKEND=default_backend, OPTIONS=options)
        )
        if not choice:
            selected = default_backend
        else:
            try:
                selected = available_backends[int(choice) - 1]
            except (ValueError, IndexError):
                _logger.warning(
                    "Invalid debugger backend choice %r, using %s",
                    choice,
                    default_backend,
                )
                selected = default_backend
        _logger.info(
            _("You selected debugger backend: {SELECTED_BACKEND}\n").format(
                SELECTED_BACKEND=selected,
            )
        )
        return selected

    def get_from_user_odpm_ide(self) -> str:
        default_ide = DEFAULT_ODPM_IDE
        options = "\n".join(
            f"{index} - {ODPM_IDE_LABELS[ide_id]}"
            for index, ide_id in enumerate(sorted(ODPM_IDE_VALUES), start=1)
        )
        choice = prompt_input(
            _(
                "Select IDE configuration to generate "
                "(Enter for default {DEFAULT_IDE}):\n{OPTIONS}\n"
            ).format(DEFAULT_IDE=default_ide, OPTIONS=options)
        )
        if not choice:
            selected = default_ide
        else:
            ordered = sorted(ODPM_IDE_VALUES)
            try:
                selected = ordered[int(choice) - 1]
            except (ValueError, IndexError):
                _logger.warning(
                    "Invalid ODPM_IDE choice %r, using %s",
                    choice,
                    default_ide,
                )
                selected = default_ide
        _logger.info(
            _("You selected IDE configuration: {SELECTED_IDE}\n").format(
                SELECTED_IDE=selected,
            )
        )
        return selected
