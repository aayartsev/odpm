"""Host-side odpm pipeline: config → project environment → compose / CI build."""

from __future__ import annotations

import os
import shlex
import sys
from argparse import Namespace

from . import constants, translations
from .check_system import SystemChecker
from .compose_runtime import should_force_recreate_compose
from .errors import ConfigError, OdpmError, PipelineError
from .config import Config
from .project_env import CreateProjectEnvironment
from .compose_service_builder import ComposeServiceBuilder
from .git.deps_lock_manager import DepsLockManager
from .host_user_env import CreateUserEnvironment
from .inside_docker_app.logger import get_module_logger
from .project_dir_manager import ProjectDirManager
from .subprocess_runner import run_logged

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
        if getattr(self.args, "version", False):
            _logger.info(
                f"{constants.PROJECT_NAME} version: {constants.ODPM_VERSION}"
            )
            raise ConfigError("", exit_code=0)
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
        self.system_checker = SystemChecker(self.config, self.project_environment)

    def prepare_project_files(self) -> None:
        project_env = self._project_environment()
        system_checker = self._system_checker()
        config = self._config()
        skip_git = getattr(self.args, "no_git_update", False)
        update_lock = getattr(self.args, "update_lock", False)
        if update_lock and skip_git:
            message = "--update-lock cannot be used together with --no-git-update"
            _logger.error(message)
            raise PipelineError(message, exit_code=1)

        lock_manager = DepsLockManager(config)
        if not skip_git and not update_lock:
            lock_manager.load()
            lock_manager.enter_apply_mode()

        if skip_git:
            config.ensure_git_repos_present()
        else:
            config.materialize_git_repos(
                skip_build_date=lock_manager.has_platform_lock()
            )
        project_env.map_folders()
        lock_manager.apply_to_platform(config.odoo_platform_project)
        lock_manager.apply_to_developing(config.developing_project)
        lock_manager.apply_to_dependencies(config.dependencies_projects)
        project_env.generate_dockerfile()
        project_env.generate_dockerignore()
        system_checker.check_docker()
        system_checker.check_running_containers()
        project_env.generate_config_file()
        ComposeServiceBuilder(config).build()
        project_env.generate_docker_compose_file()
        system_checker.check_docker_compose()
        if not skip_git:
            project_env.checkout_dependencies(lock_manager=lock_manager)
            if update_lock:
                lock_manager.collect_and_save(
                    developing=config.developing_project,
                )
            elif lock_manager.apply_mode:
                lock_manager.verify_after_checkout(
                    platform=config.odoo_platform_project,
                    developing=config.developing_project,
                    dependencies=config.dependencies_projects,
                )
        project_env.update_links()

    def handle_build_image(self) -> bool:
        """Run CI image build. Returns True when the pipeline should stop."""
        if not self.args.build_image:
            return False
        config = self._config()
        if not config.policy.allow_build_image:
            message = translations.get_translation(
                translations.BUILD_IMAGE_REQUIRES_CI_SCENARIO
            )
            _logger.error(message)
            raise PipelineError(message, exit_code=1)
        self._project_environment().build_ci_image()
        return True

    def configure_vscode(self) -> None:
        if self._config().policy.skip_vscode:
            return
        project_env = self._project_environment()
        project_env.update_vscode_debugger_launcher()
        project_env.generate_vscode_settings_json()

    def build_compose_up_argv(
        self, config: Config, *, force_recreate: bool | None = None
    ) -> list[str]:
        if force_recreate is None:
            force_recreate = should_force_recreate_compose(config)
        argv = shlex.split(config.docker_compose_command) + ["up"]
        if config.no_log_prefix:
            argv.append("--no-log-prefix")
        argv.append("--abort-on-container-exit")
        if force_recreate:
            argv.append("--force-recreate")
        else:
            _logger.info(
                "Compose stack is healthy; starting without --force-recreate"
            )
        return argv

    def start_containers(self) -> None:
        config = self._config()
        returncode = run_logged(
            self.build_compose_up_argv(config),
            cwd=config.project_dir,
        )
        if returncode != 0:
            message = translations.get_translation(
                translations.COMPOSE_UP_FAILED
            ).format(EXIT_CODE=returncode)
            _logger.error(message)
            raise PipelineError(message, exit_code=returncode)

    def run(self) -> None:
        try:
            self.setup()
            self.prepare_project_files()
            if self.handle_build_image():
                return
            self.configure_vscode()
            os.chdir(self._config().project_dir)
            if getattr(self.args, "update_lock", False):
                _logger.info("Git dependency lock updated; container start skipped")
                return
            if self.args.skip_start:
                _logger.info("Start of instace will be skipped")
                return
            try:
                self.start_containers()
            except KeyboardInterrupt:
                _logger.info("Control+C pressed")
                sys.exit()
        except OdpmError as exc:
            sys.exit(exc.exit_code)

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
