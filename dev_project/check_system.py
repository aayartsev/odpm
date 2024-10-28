import subprocess
import platform
import json
import os
from pathlib import Path
from typing import NamedTuple

if platform.system() == "Linux":
    import pwd
    import grp

from . import constants
from . import translations
from .host_config import Config

from .inside_docker_app.logger import get_module_logger
from .inside_docker_app import utils

from .protocols import SystemCheckerProtocol

_logger = get_module_logger(__name__)

class ContainerData(NamedTuple):
    ports: list[int]
    container_id: str

class SystemChecker(SystemCheckerProtocol):

    def __init__(self, config:Config) -> None:
        self.config = config
        self.config.system_checker = self
        if self.config.check_system:
            self.check_git()
        self.check_file_system()
    
    def check_git(self) -> None:
        process_result = subprocess.run(["git",  "--version"], capture_output=True)
        output_string = process_result.stdout.decode("utf-8")
        if constants.GIT_WORKING_MESSAGE not in output_string:
            _logger.error(translations.get_translation(translations.IS_GIT_INSTALLED))
            exit(1)
    
    def get_groups(self, user:str) -> list:
        gids = [g.gr_gid for g in grp.getgrall() if user in g.gr_mem]
        gid = pwd.getpwnam(user).pw_gid
        gids.append(grp.getgrgid(gid).gr_gid)
        return [grp.getgrgid(gid).gr_name for gid in gids]

    def check_docker(self) -> None:
        if platform.system() == "Linux":
            groups = self.get_groups(constants.CURRENT_USER)
            if constants.LINUX_DOCKER_GROUPNAME not in groups:
                _logger.error(translations.get_translation(translations.USER_NOT_IN_DOCKER_GROUP).format(
                        CURRENT_USER=constants.CURRENT_USER,
                        LINUX_DOCKER_GROUPNAME=constants.LINUX_DOCKER_GROUPNAME,
                    )
                )
                exit(1)
        process_result = subprocess.run(["docker",  "info"], capture_output=True)
        output_string = process_result.stdout.decode("utf-8")
        if constants.DOCKER_WORKING_MESSAGE not in output_string:
            _logger.error(translations.get_translation(translations.CAN_NOT_CONNECT_DOCKER))
            exit(1)
        
        process_result = subprocess.run(["docker",  "images", "--format", "'{{json .}}'"], capture_output=True)
        output_string = process_result.stdout.decode("utf-8")
        result_list = []
        for record in output_string.split("\n"):
            if record:
                new_record = json.loads(record.replace("'", ""))
                if self.config.odoo_image_name == new_record["Repository"]:
                    result_list.append(new_record)
        if not result_list:
            self.config.project_env.build_image()
    
    def check_running_containers(self) -> None:
        ports_to_check = [
            self.config.user_env.odoo_port,
            self.config.user_env.debugger_port,
            self.config.user_env.postgres_port,
        ]
        def get_ports(data_port_string):
            busy_ports = []
            port_items =  data_port_string.split(",")
            for port_item in port_items:
                port_item = port_item.strip()
                host_port = port_item.split("->")
                if len(host_port) >= 2:
                    host_port = host_port[1].split("/")[0]
                else:
                    host_port = 0
                busy_ports.append(int(host_port))
            return busy_ports
        process_result = subprocess.run(["docker",  "container", "ls", "--format", "'{{json .}}'"], capture_output=True)
        output_string = process_result.stdout.decode("utf-8")
        result_list = []
        for record in output_string.split("\n"):
            if record:
                new_record = json.loads(record.replace("'", ""))
                data_port_string = new_record["Ports"]
                busy_ports = get_ports(data_port_string)
                result_list.append(ContainerData(
                    ports=busy_ports,
                    container_id=new_record["ID"]
                ))

        for result in result_list:
            used_ports = list(set(result.ports) & set(ports_to_check))
            if used_ports:
                subprocess.run(["docker",  "stop", result.container_id])

    def check_docker_compose(self) -> None:
        self.config.no_log_prefix = True
        process_result = subprocess.run(["docker-compose",  "version"], capture_output=True)
        output_string = process_result.stdout.decode("utf-8")
        output_string = output_string.lower().replace("-"," ")
        if constants.DOCKER_COMPOSE_WORKING_MESSAGE not in output_string:
            _logger.error(translations.get_translation(translations.CAN_NOT_GET_DOCKER_COMPOSE_INFO))
            exit(1)
        up_help_result = subprocess.run(["docker-compose",  "up", "--help"], capture_output=True)
        up_help_string = up_help_result.stdout.decode("utf-8")
        output_string = output_string.lower().replace("-"," ")
        if constants.NO_LOG_PREFIX not in up_help_string:
            self.config.no_log_prefix = False
    
    def check_file_system(self) -> None:
        for dir_path in [
            self.config.user_env.backups,
            self.config.user_env.odoo_projects_dir,
        ]:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except BaseException:
                    _logger.error(translations.get_translation(translations.CAN_NOT_CREATE_DIR).format(
                        dir_path=dir_path,
                    ))
                    exit(1)
        if not os.path.exists(self.config.user_env.odoo_src_dir):
            os.mkdir(self.config.user_env.odoo_src_dir)
        os.chdir(self.config.user_env.odoo_src_dir)
        odoo_src_state_bytes = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True)
        odoo_src_state_string = odoo_src_state_bytes.stdout.decode("utf-8")
        if not "true" in odoo_src_state_string:
            clone_odoo = input(translations.get_translation(translations.DO_YOU_WANT_CLONE_ODOO))
            if clone_odoo and clone_odoo.lower() == "y":
                self.config.project_env.download_odoo_repository()
            else:
                _logger.error(translations.get_translation(translations.CHECK_ODOO_REPO).format(
                    odoo_src_dir= self.config.user_env.odoo_src_dir
                ))
                exit(1)
    
    def check_free_space_for_odoo_developing(self):
        free_space = utils.get_free_space(Path.home())
        if free_space < constants.FREE_SPACE_FOR_USAGE:
            _logger.error(translations.get_translation(translations.YOU_NEED_TO_HAVE_FREE_SPACE).format(
                NECESSARY_FREE_SPACE=constants.FREE_SPACE_FOR_USAGE,
                DIR_FOR_FREE_SPACE=Path.home(),
            ))
            exit(1)
