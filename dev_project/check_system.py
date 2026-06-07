import json
import os
import platform
from pathlib import Path
from typing import NamedTuple

from . import constants, translations
from .config import Config
from .errors import SubprocessError, SystemCheckError
from .inside_docker_app import utils
from .logging import get_module_logger
from .project_env import CreateProjectEnvironment
from .protocols import SystemCheckerProtocol
from .subprocess_runner import run_checked, run_logged, run_or_raise

_logger = get_module_logger(__name__)


class ContainerData(NamedTuple):
    ports: list[int]
    container_id: str


class SystemChecker(SystemCheckerProtocol):
    def __init__(
        self,
        config: Config,
        project_environment: CreateProjectEnvironment,
    ) -> None:
        self.config = config
        self.project_environment = project_environment
        if self.config.check_system:
            self.check_git()
        self.check_file_system()

    def check_git(self) -> None:
        message = translations.get_translation(translations.IS_GIT_INSTALLED)
        self._run_required_command(
            ["git", "--version"],
            expected_in_stdout=constants.GIT_WORKING_MESSAGE,
            error_message=message,
        )

    def _run_required_command(
        self,
        argv: list[str],
        *,
        expected_in_stdout: str,
        error_message: str,
    ):
        try:
            result = run_or_raise(argv)
        except SubprocessError as exc:
            _logger.error(error_message)
            raise SystemCheckError(error_message) from exc
        if expected_in_stdout not in result.stdout:
            _logger.error(error_message)
            raise SystemCheckError(error_message)
        return result

    def get_system_groups(self, user: str) -> list:
        import grp
        import pwd

        gids = [g.gr_gid for g in grp.getgrall() if user in g.gr_mem]
        gid = pwd.getpwnam(user).pw_gid
        gids.append(grp.getgrgid(gid).gr_gid)
        return [grp.getgrgid(gid).gr_name for gid in gids]

    def check_docker(self) -> None:
        if platform.system() == "Linux":
            groups = self.get_system_groups(constants.HOST_USER)
            if constants.LINUX_DOCKER_GROUPNAME not in groups:
                message = translations.get_translation(
                    translations.USER_NOT_IN_DOCKER_GROUP
                ).format(
                    CURRENT_USER=constants.HOST_USER,
                    LINUX_DOCKER_GROUPNAME=constants.LINUX_DOCKER_GROUPNAME,
                )
                _logger.error(message)
                raise SystemCheckError(message)
        message = translations.get_translation(translations.CAN_NOT_CONNECT_DOCKER)
        self._run_required_command(
            ["docker", "info"],
            expected_in_stdout=constants.DOCKER_WORKING_MESSAGE,
            error_message=message,
        )

        self.project_environment.ensure_base_image()

    def check_running_containers(self) -> None:
        ports_to_check = [
            self.config.user_env.odoo_port,
            self.config.user_env.debugger_port,
            self.config.user_env.postgres_port,
            self.config.user_env.gevent_port,
        ]

        def get_ports(data_port_string):
            busy_ports = []
            port_items = data_port_string.split(",")
            for port_item in port_items:
                port_item = port_item.strip()
                port_map = port_item.split("->")
                if len(port_map) >= 2:
                    host_port = port_map[0].split(":")[-1]
                else:
                    host_port = "0"
                if "-" in host_port:
                    busy_ports.extend([int(item) for item in host_port.split("-")])
                else:
                    busy_ports.append(int(host_port))
            return busy_ports

        try:
            process_result = run_or_raise(
                ["docker", "container", "ls", "--format", "'{{json .}}'"],
            )
        except SubprocessError as exc:
            message = translations.get_translation(
                translations.CAN_NOT_LIST_DOCKER_CONTAINERS
            ).format(DETAILS=str(exc))
            _logger.error(message)
            raise SystemCheckError(message) from exc
        output_string = process_result.stdout
        result_list = []
        for record in output_string.split("\n"):
            if record:
                new_record = json.loads(record.replace("'", ""))
                data_port_string = new_record["Ports"]
                busy_ports = get_ports(data_port_string)
                result_list.append(
                    ContainerData(ports=busy_ports, container_id=new_record["ID"])
                )

        for result in result_list:
            used_ports = list(set(result.ports) & set(ports_to_check))
            if used_ports:
                run_logged(["docker", "stop", result.container_id])

    def check_docker_compose(self) -> None:
        self.config.no_log_prefix = True
        docker_compose_working_message_in_output_string = False
        for command in constants.LIST_OF_DOCKER_COMPOSE_COMMANDS:
            up_help_command_list = [*command.split(" "), "up", "--help"]
            up_help_result = run_checked(up_help_command_list)
            if constants.NO_LOG_PREFIX not in up_help_result.stdout:
                self.config.no_log_prefix = False
            version_command_list = [*command.split(" "), "version"]
            process_result = run_checked(version_command_list)
            output_string = process_result.stdout.lower().replace("-", " ")
            if constants.DOCKER_COMPOSE_WORKING_MESSAGE in output_string:
                docker_compose_working_message_in_output_string = True
                self.config.docker_compose_command = command
                break
        if not docker_compose_working_message_in_output_string:
            message = translations.get_translation(
                translations.CAN_NOT_GET_DOCKER_COMPOSE_INFO
            )
            _logger.error(message)
            raise SystemCheckError(message)

    def check_file_system(self) -> None:
        for dir_path in [
            self.config.user_env.backups,
            self.config.user_env.odoo_projects_dir,
        ]:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except BaseException:
                    message = translations.get_translation(
                        translations.CAN_NOT_CREATE_DIR
                    ).format(
                        dir_path=dir_path,
                    )
                    _logger.error(message)
                    raise SystemCheckError(message)
        # todo сделать переключатель

    def check_free_space_for_odoo_developing(
        self, free_space_size: float = constants.FREE_SPACE_FOR_USAGE
    ) -> None:
        free_space = utils.get_free_space(Path.home())
        if free_space < free_space_size:
            message = translations.get_translation(
                translations.YOU_NEED_TO_HAVE_FREE_SPACE
            ).format(
                NECESSARY_FREE_SPACE=free_space_size,
                DIR_FOR_FREE_SPACE=Path.home(),
            )
            _logger.error(message)
            raise SystemCheckError(message)
