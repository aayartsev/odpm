import json
import os
import platform
from typing import NamedTuple

from . import constants
from .docker_capabilities import probe_compose_command_from_candidates
from .translations import _
from .config import Config
from .errors import SubprocessError, SystemCheckError
from .logging import get_module_logger
from .project_env import CreateProjectEnvironment
from .project_env.services import BaseImageService
from .protocols import SystemCheckerProtocol
from .subprocess_runner import run_checked, run_logged, run_or_raise
from .system_check_policy import SystemCheckPolicy

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
        policy = SystemCheckPolicy.from_config(config)
        if policy.file_system_on_init:
            self.check_file_system()

    def check_git(self) -> None:
        message = _('Did you install git?')
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

    def check_docker_daemon(self) -> None:
        """Probe Docker group membership and ``docker info`` (daemon reachability)."""
        if platform.system() == "Linux":
            groups = self.get_system_groups(constants.HOST_USER)
            if constants.LINUX_DOCKER_GROUPNAME not in groups:
                message = _('You need to add your user {CURRENT_USER} to group {LINUX_DOCKER_GROUPNAME} run this command as root or sudo:  usermod -a -G {LINUX_DOCKER_GROUPNAME} {CURRENT_USER} then reboot your computer').format(
                    CURRENT_USER=constants.HOST_USER,
                    LINUX_DOCKER_GROUPNAME=constants.LINUX_DOCKER_GROUPNAME,
                )
                _logger.error(message)
                raise SystemCheckError(message)
        message = _('Cannot connect to the Docker daemon. Is the docker daemon running?')
        self._run_required_command(
            ["docker", "info"],
            expected_in_stdout=constants.DOCKER_WORKING_MESSAGE,
            error_message=message,
        )

    def ensure_base_image(self) -> None:
        BaseImageService(self.project_environment).ensure_base_image()

    def check_docker(self) -> None:
        policy = SystemCheckPolicy.from_config(self.config)
        if not policy.skip_docker_daemon:
            self.check_docker_daemon()
        if not policy.skip_ensure_base_local:
            self.ensure_base_image()

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
            message = _('Cannot list Docker containers: {DETAILS}').format(DETAILS=str(exc))
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
        capabilities = probe_compose_command_from_candidates(
            constants.LIST_OF_DOCKER_COMPOSE_COMMANDS,
            run_checked=run_checked,
        )
        if capabilities is None:
            message = _('Cannot get docker-compose info, did you install it?')
            _logger.error(message)
            raise SystemCheckError(message)
        self.config.docker_compose_command = capabilities.compose_command
        self.config.no_log_prefix = capabilities.supports_no_log_prefix
        self.config.docker_capabilities = capabilities

    def _platform_git_repo_ready(self) -> bool:
        odoo_src_dir = self.config.odoo_src_dir
        if not odoo_src_dir or not os.path.isdir(odoo_src_dir):
            return False
        if not os.path.exists(os.path.join(odoo_src_dir, ".git")):
            return False
        try:
            result = run_or_raise(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=odoo_src_dir,
            )
        except SubprocessError:
            return False
        return "true" in result.stdout

    def _ensure_platform_sources(self) -> None:
        policy = self.config.policy
        if policy.is_ci():
            return
        if not (policy.is_developer() or policy.is_server()):
            return
        platform = getattr(self.config, "odoo_platform_project", None)
        if (
            platform
            and getattr(platform, "link_type", None) == constants.GITLINK_TYPE_FILE
        ):
            return
        if not self._platform_git_repo_ready():
            message = _('Platform git repository at {odoo_src_dir} is not ready yet; cloning will run during prepare (git.materialize step).').format(odoo_src_dir=self.config.odoo_src_dir)
            _logger.warning(message)

    def check_file_system(self) -> None:
        policy = SystemCheckPolicy.from_config(self.config)
        dirs = [self.config.user_env.odoo_projects_dir]
        if not policy.relaxed_file_system:
            dirs.insert(0, self.config.user_env.backups)
        for dir_path in dirs:
            if not dir_path:
                continue
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except BaseException as err:
                    message = _('Cannot create dir, {dir_path}, please check it').format(
                        dir_path=dir_path,
                    )
                    _logger.error(message)
                    raise SystemCheckError(message) from err
        self._ensure_platform_sources()
