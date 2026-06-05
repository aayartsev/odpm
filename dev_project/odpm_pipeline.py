"""Host-side odpm pipeline: config → project environment → compose / CI build."""

from __future__ import annotations

import os
import sys
from argparse import Namespace

from . import translations
from .check_system import SystemChecker
from .host_config import Config
from .host_project_env import CreateProjectEnvironment
from .host_start_string_builder import StartStringBuilder
from .host_user_env import CreateUserEnvironment
from .inside_docker_app.logger import get_module_logger
from .project_dir_manager import ProjectDirManager

_logger = get_module_logger(__name__)


class OdpmPipeline:
    def __init__(
        self,
        args: Namespace,
        program_dir: str,
        start_dir: str | None = None,
    ) -> None:
        self.args = args
        self.program_dir = program_dir
        self.start_dir = start_dir or os.environ.get("PWD") or os.getcwd()
        self.pd_manager: ProjectDirManager | None = None
        self.config: Config | None = None
        self.project_environment: CreateProjectEnvironment | None = None
        self.system_checker: SystemChecker | None = None

    def setup(self) -> None:
        self.pd_manager = ProjectDirManager(
            self.start_dir, self.args, self.program_dir
        )
        user_environment = CreateUserEnvironment(self.pd_manager)
        self.config = Config(
            self.pd_manager,
            self.args,
            self.program_dir,
            user_environment,
        )
        self.project_environment = CreateProjectEnvironment(self.config)
        self.system_checker = SystemChecker(self.config)

    def prepare_project_files(self) -> None:
        project_env = self._project_environment()
        system_checker = self._system_checker()
        config = self._config()
        project_env.map_folders()
        project_env.generate_dockerfile()
        system_checker.check_docker()
        system_checker.check_running_containers()
        project_env.generate_config_file()
        StartStringBuilder(config)
        project_env.generate_docker_compose_file()
        system_checker.check_docker_compose()
        project_env.checkout_dependencies()
        project_env.update_links()

    def handle_build_image(self) -> bool:
        """Run CI image build. Returns True when the pipeline should stop."""
        if not self.args.build_image:
            return False
        config = self._config()
        if not config.policy.allow_build_image:
            _logger.error(
                translations.get_translation(
                    translations.BUILD_IMAGE_REQUIRES_CI_SCENARIO
                )
            )
            sys.exit(1)
        self._project_environment().build_ci_image()
        return True

    def configure_vscode(self) -> None:
        if self._config().policy.skip_vscode:
            return
        project_env = self._project_environment()
        project_env.update_vscode_debugger_launcher()
        project_env.generate_vscode_settings_json()

    def start_containers(self) -> None:
        config = self._config()
        if config.no_log_prefix:
            compose_cmd = (
                f"{config.docker_compose_command} up --no-log-prefix "
                "--abort-on-container-exit --force-recreate"
            )
        else:
            compose_cmd = (
                f"{config.docker_compose_command} up "
                "--abort-on-container-exit --force-recreate"
            )
        os.system(compose_cmd)

    def run(self) -> None:
        self.setup()
        self.prepare_project_files()
        if self.handle_build_image():
            return
        self.configure_vscode()
        os.chdir(self._config().project_dir)
        if self.args.skip_start:
            _logger.info("Start of instace will be skipped")
            return
        try:
            self.start_containers()
        except KeyboardInterrupt:
            _logger.info("Control+C pressed")
            sys.exit()

    def _config(self) -> Config:
        if self.config is None:
            raise RuntimeError("OdpmPipeline.setup() was not called")
        return self.config

    def _project_environment(self) -> CreateProjectEnvironment:
        if self.project_environment is None:
            raise RuntimeError("OdpmPipeline.setup() was not called")
        return self.project_environment

    def _system_checker(self) -> SystemChecker:
        if self.system_checker is None:
            raise RuntimeError("OdpmPipeline.setup() was not called")
        return self.system_checker
