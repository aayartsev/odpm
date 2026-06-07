"""Host-side odpm pipeline: config → project environment → compose / CI build."""

from __future__ import annotations

import os
import shlex
import sys

from . import constants, translations
from .check_system import SystemChecker
from .compose.runtime import should_force_recreate_compose
from .errors import ConfigError, OdpmError, PipelineError
from .config import Config
from .project_env import CreateProjectEnvironment
from .host.user_env import CreateUserEnvironment
from .logging import get_module_logger
from .project_dir_manager import ProjectDirManager
from .host.cli.args import OdpmCliArgs
from .project_materializer import ProjectMaterializer
from .subprocess_runner import run_logged
from .system_check_policy import SystemCheckPolicy

_logger = get_module_logger(__name__)

class OdpmPipeline:
    def __init__(
        self,
        cli_args: OdpmCliArgs,
        program_dir: str,
        start_dir: str | None = None,
    ) -> None:
        self.cli_args = cli_args
        self.program_dir = program_dir
        self.start_dir = start_dir or os.getcwd() or os.environ.get("PWD", "")
        self.pd_manager: ProjectDirManager | None = None
        self.config: Config | None = None
        self.project_environment: CreateProjectEnvironment | None = None
        self.system_checker: SystemChecker | None = None

    def setup(self, *, for_plan: bool = False) -> None:
        if self.cli_args.version:
            _logger.info(
                f"{constants.PROJECT_NAME} version: {constants.ODPM_VERSION}"
            )
            raise ConfigError("", exit_code=0)
        self.pd_manager = ProjectDirManager(
            self.start_dir,
            self.cli_args,
            self.program_dir,
            sync_templates=not for_plan,
        )
        self.cli_args = self.pd_manager.arguments
        user_environment = CreateUserEnvironment(self.pd_manager)
        self.config = Config(
            self.pd_manager,
            self.cli_args,
            self.program_dir,
            user_environment,
        )
        self.project_environment = CreateProjectEnvironment(self.config)
        self.system_checker = SystemChecker(self.config, self.project_environment)
        policy = SystemCheckPolicy.from_config(self.config)
        if policy.beginner_git:
            self.system_checker.check_git()
        self.project_environment.attach_system_checker(self.system_checker)

    def prepare_project_files(self) -> None:
        ProjectMaterializer().run(
            self._config(),
            self._project_environment(),
            self._system_checker(),
            self.cli_args,
        )

    def print_plan(self) -> int:
        from .plan import OdpmPlanner, format_plan
        from .plan.format import plan_has_required_changes, resolve_plan_format

        config = self._config()
        plan = OdpmPlanner.build(
            config,
            self.cli_args,
            self._project_environment(),
        )
        text = format_plan(plan, self.cli_args, config)
        if resolve_plan_format(self.cli_args) == "json":
            print(text, flush=True)
        else:
            _logger.info(text)
        if self.cli_args.plan_strict and plan_has_required_changes(plan):
            return 1
        return 0

    def handle_build_image(self) -> bool:
        """Run CI image build. Returns True when the pipeline should stop."""
        if not self.cli_args.build_image:
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
            from .plan.cli import is_plan_mode

            for_plan = is_plan_mode(self.cli_args)
            self.setup(for_plan=for_plan)

            if for_plan:
                exit_code = self.print_plan()
                if exit_code:
                    sys.exit(exit_code)
                return
            self.prepare_project_files()
            if self.handle_build_image():
                return
            self.configure_vscode()
            if self.cli_args.update_lock:
                _logger.info("Git dependency lock updated; container start skipped")
                return
            if self.cli_args.skip_start:
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
