import os
import platform
from configparser import ConfigParser
from pathlib import Path
from typing import TypedDict

from .. import constants
from ..translations import _
from ..errors import ConfigError
from ..interactive import prompt_input, stdin_is_interactive
from ..logging import get_module_logger
from ..project_dir_manager import ProjectDirManager

_logger = get_module_logger(__name__)


class EnvData(TypedDict):
    BACKUP_DIR: str
    ODOO_PROJECTS_DIR: str
    PATH_TO_SSH_KEY: str
    ODOO_PORT: int
    POSTGRES_PORT: int
    DEBUGGER_PORT: int
    GEVENT_PORT: int
    ODPM_SCENARIO: str


class CreateUserEnvironment:
    def __init__(self, pd_manager: ProjectDirManager):
        self.pd_manager = pd_manager
        self.config_home_dir = self.pd_manager.home_config_dir
        self.env_file = self.get_env_file_path()
        self.parse_env_file()

    def get_env_file_path(self) -> str:
        local_env_file = os.path.join(
            self.pd_manager.project_path, constants.ENV_FILE_NAME
        )
        if os.path.exists(local_env_file):
            return local_env_file
        if not os.path.exists(self.config_home_dir):
            os.makedirs(self.config_home_dir)
        # TODO we need to write method that will create default .env file
        local_env_file = os.path.join(self.config_home_dir, constants.ENV_FILE_NAME)
        if not os.path.exists(local_env_file):
            if stdin_is_interactive():
                self.create_env_file(local_env_file)
            else:
                self.create_env_file_noninteractive(local_env_file)
        return local_env_file

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

    def create_env_file(self, local_env_file: str) -> None:
        new_env_data = self._build_env_data_interactive()
        self._write_env_file(local_env_file, new_env_data)

    def create_env_file_noninteractive(self, local_env_file: str) -> None:
        if not self._has_noninteractive_env_configuration():
            message = _('Non-interactive mode requires an existing .env file in the project directory or under ~/.odpm/.env. Create it manually or set environment variables (BACKUP_DIR, ODOO_PROJECTS_DIR, PATH_TO_SSH_KEY, ODOO_PORT, POSTGRES_PORT, DEBUGGER_PORT, GEVENT_PORT, ODPM_SCENARIO) before the first run.')
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
        with open(local_env_file, "w") as env_file:
            for key_name, value in new_env_data.items():
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
        return EnvData(
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

    def _build_env_data_interactive(self) -> EnvData:
        return EnvData(
            BACKUP_DIR=self.get_from_user_backup_dir(),
            ODOO_PROJECTS_DIR=self.get_from_user_odoo_projects_src_dir(),
            PATH_TO_SSH_KEY=self.get_from_user_path_to_ssh_key(),
            ODOO_PORT=self.get_from_user_odoo_port(),
            POSTGRES_PORT=self.get_from_user_postgres_port(),
            DEBUGGER_PORT=self.get_from_user_debugger_port(),
            GEVENT_PORT=self.get_from_user_gevent_port(),
            ODPM_SCENARIO=self.get_from_user_odpm_scenario(),
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

    def get_from_user_path_to_ssh_key(self) -> str:
        ssh_path = prompt_input(_("Set path to your SSH key for GitHub. How to create it you can read here: https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent. Press 'Enter' leave empty value, in this case system will try to use default system ssh key for GitHub:\n"))
        ssh_path_name = ssh_path
        if not ssh_path:
            ssh_path_name = _('You did not selected any path to ssh key')
        _logger.info(
            _('You select this ssh path key: {SELECTED_SSH_KEY_PATH}\n').format(
                SELECTED_SSH_KEY_PATH=ssh_path_name,
            )
        )
        return ssh_path

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
