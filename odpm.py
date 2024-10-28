#!/bin/python3
import os
import sys

from dev_project.translations import _
from dev_project.check_system import SystemChecker
from dev_project.host_project_env import CreateProjectEnvironment
from dev_project.host_user_env import CreateUserEnvironment
from dev_project.inside_docker_app.parse_args import args
from dev_project.host_start_string_builder import StartStringBuilder
from dev_project.project_dir_manager import ProjectDirManager
from dev_project.host_config import Config

from dev_project.inside_docker_app.logger import get_module_logger

_logger = get_module_logger(__name__)

def main() -> None:
    program_dir_path = os.path.dirname(os.path.abspath(__file__))
    start_dir_path = os.getenv("PWD", "")
    pd_manager = ProjectDirManager(start_dir_path, args, program_dir_path)
    user_environment = CreateUserEnvironment(pd_manager)
    pd_manager.check_project_dir()
    config = Config(
        pd_manager,
        args,
        program_dir_path,
        user_environment,
    )
    project_environment = CreateProjectEnvironment(config)
    system_checker = SystemChecker(config)
    project_environment.map_folders()
    project_environment.generate_dockerfile()
    system_checker.check_docker()
    system_checker.check_running_containers()
    project_environment.generate_config_file()
    StartStringBuilder(config)
    project_environment.generate_docker_compose_file()
    system_checker.check_docker_compose()
    project_environment.checkout_dependencies()
    project_environment.update_links()
    project_environment.update_vscode_debugger_launcher()
    project_environment.generate_vscode_settings_json()

    os.chdir(config.project_dir)

    try:
        if config.no_log_prefix:
            os.system(f"""docker compose up --no-log-prefix --abort-on-container-exit --force-recreate""")
        else:
            os.system(f"""docker compose up --abort-on-container-exit --force-recreate""")
    except KeyboardInterrupt:
        _logger.info("Control+C pressed")
        sys.exit()

if __name__ == "__main__":
    main()
