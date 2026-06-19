"""Host-side odpm pipeline: config → project environment → compose / CI build."""

from __future__ import annotations

import os
import sys

from . import constants, host_summaries
from .check_system import SystemChecker
from .errors import ConfigError, OdpmError
from .config import Config
from .project_env import CreateProjectEnvironment
from .runtime_coordinator import RuntimeCoordinator
from .host.user_env import CreateUserEnvironment
from .logging import get_module_logger
from .project_dir_manager import ProjectDirManager
from .host.cli.args import OdpmCliArgs
from .project_materializer import ProjectMaterializer
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
        self._import_secrets_if_requested()
        self.project_environment = CreateProjectEnvironment(self.config)
        self.system_checker = SystemChecker(self.config, self.project_environment)
        policy = SystemCheckPolicy.from_config(self.config)
        if policy.beginner_git:
            self.system_checker.check_git()
        self.project_environment.attach_system_checker(self.system_checker)

    def _import_secrets_if_requested(self) -> None:
        if not self.cli_args.secrets_file:
            return
        from .project_env.secrets import import_secrets_from_path

        import_secrets_from_path(self.config.project_dir, self.cli_args.secrets_file)

    def prepare_project_files(self) -> None:
        host_summaries.log_prepare_started()
        ProjectMaterializer().run(
            self._config(),
            self._project_environment(),
            self._system_checker(),
            self.cli_args,
        )
        host_summaries.log_prepare_completed()

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

    def _runtime(self) -> RuntimeCoordinator:
        return RuntimeCoordinator(
            self.cli_args,
            self._config(),
            self._project_environment(),
        )

    def handle_build_image(self) -> bool:
        return self._runtime().handle_build_image()

    def configure_vscode(self) -> None:
        self._runtime().configure_vscode()

    def build_compose_up_argv(self, config: Config, *, force_recreate: bool | None = None) -> list[str]:
        return RuntimeCoordinator(
            self.cli_args, config, self._project_environment()
        ).build_compose_up_argv(force_recreate=force_recreate)

    def start_containers(self) -> None:
        self._runtime().start_containers()

    def run(self) -> None:
        try:
            from .plan.cli import is_database_mode, is_manifest_mode, is_plan_mode

            for_plan = is_plan_mode(self.cli_args)
            for_database = is_database_mode(self.cli_args)
            for_manifest = is_manifest_mode(self.cli_args)
            self.setup(for_plan=for_plan or for_database or for_manifest)

            if for_plan:
                exit_code = self.print_plan()
                if exit_code:
                    sys.exit(exit_code)
                return
            if for_database:
                from .database.commands import run_database_command

                exit_code = run_database_command(self.cli_args, self._config())
                if exit_code:
                    sys.exit(exit_code)
                return
            if for_manifest:
                from .manifest.commands import run_manifest_command

                exit_code = run_manifest_command(self.cli_args, self._config())
                if exit_code:
                    sys.exit(exit_code)
                return
            self.prepare_project_files()
            self._runtime().run_after_prepare()
        except OdpmError as exc:
            message = str(exc)
            if message:
                _logger.error("%s", message)
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
