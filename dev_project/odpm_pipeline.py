"""Host-side odpm pipeline: config → project environment → compose / CI build."""

from __future__ import annotations

import os
import sys

from . import constants, host_summaries
from .check_system import SystemChecker
from .errors import ConfigError, OdpmError
from .project_env import CreateProjectEnvironment
from .runtime_coordinator import RuntimeCoordinator
from .host.user_env import CreateUserEnvironment
from .logging import get_module_logger
from .project_dir_manager import ProjectDirManager
from .host.cli.args import OdpmCliArgs
from .host.ports import BootstrapHandle, PipelinePorts
from .project_materializer import ProjectMaterializer
from .secrets_providers.session import SecretsFetchSession
from .system_check_policy import SystemCheckPolicy, cli_allows_ci_explicit_mode
from .translations import _
from .host.version_info import format_odpm_version_line
from .config.assembly import (
    assemble_project,
    host_context_from_assembled,
    ports_from_assembled,
)

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
        self.ports: PipelinePorts | None = None
        self.project_environment: CreateProjectEnvironment | None = None
        self.system_checker: SystemChecker | None = None

    def setup(self, *, for_plan: bool = False) -> None:
        if self.cli_args.version:
            _logger.info("%s", format_odpm_version_line(self.program_dir))
            raise ConfigError("", exit_code=0)
        self.pd_manager = ProjectDirManager(
            self.start_dir,
            self.cli_args,
            self.program_dir,
            sync_templates=not for_plan,
        )
        self.cli_args = self.pd_manager.arguments
        secrets_session = SecretsFetchSession()
        user_environment = CreateUserEnvironment(self.pd_manager)
        config = assemble_project(
            self.pd_manager,
            self.cli_args,
            self.program_dir,
            user_environment,
            secrets_fetch_session=secrets_session,
        )
        bootstrap = BootstrapHandle(_assembled=config)
        self.project_environment = CreateProjectEnvironment(bootstrap)
        self.system_checker = SystemChecker(bootstrap, self.project_environment)
        policy = SystemCheckPolicy.from_host_context(
            host_context_from_assembled(config)
        )
        if policy.beginner_git:
            self.system_checker.check_git()
        self.project_environment.attach_system_checker(self.system_checker)
        self.ports = ports_from_assembled(
            config,
            self.project_environment,
            self.cli_args,
        )

    def _ports(self) -> PipelinePorts:
        if self.ports is None:
            raise RuntimeError("OdpmPipeline.setup() was not called")
        return self.ports

    def prepare_project_files(self) -> None:
        host_summaries.log_prepare_started()
        ProjectMaterializer().run(
            self._ports(),
            self._system_checker(),
        )
        host_summaries.log_prepare_completed()

    def print_plan(self) -> int:
        from .plan import OdpmPlanner, format_plan  # noqa: PLC0415  # optional
        from .plan.format import (  # noqa: PLC0415  # optional
            plan_has_required_changes,
            resolve_plan_format,
        )

        ports = self._ports()
        plan = OdpmPlanner.build(
            ports,
            project_env=self._project_environment(),
        )
        text = format_plan(plan, self.cli_args, ports.plan.host_ctx)
        if resolve_plan_format(self.cli_args) == "json":
            print(text, flush=True)
        else:
            _logger.info(text)
        if self.cli_args.plan_strict and plan_has_required_changes(plan):
            return 1
        return 0

    def _runtime(self) -> RuntimeCoordinator:
        return RuntimeCoordinator(self._ports().runtime)

    def handle_build_image(self) -> bool:
        return self._runtime().handle_build_image()

    def configure_vscode(self) -> None:
        self._runtime().configure_vscode()

    def build_compose_up_argv(self, *, force_recreate: bool | None = None) -> list[str]:
        return self._runtime().build_compose_up_argv(force_recreate=force_recreate)

    def start_containers(self) -> None:
        self._runtime().start_containers()

    def run(self) -> None:
        try:
            from .plan.cli import (  # noqa: PLC0415  # optional
                is_database_host_mode,
                is_image_mode,
                is_manifest_mode,
                is_modules_mode,
                is_plan_mode,
                is_run_mode,
            )

            for_plan = is_plan_mode(self.cli_args)
            for_database_host = is_database_host_mode(self.cli_args)
            for_manifest = is_manifest_mode(self.cli_args)
            for_modules = is_modules_mode(self.cli_args)
            for_run = is_run_mode(self.cli_args)
            for_image = is_image_mode(self.cli_args)
            # Lightweight setup (no template sync) only for host tooling.
            # Stack database / up / scaffold need full setup like bare up today.
            self.setup(
                for_plan=for_plan
                or for_database_host
                or for_manifest
                or for_modules
                or for_run
            )

            if for_plan:
                exit_code = self.print_plan()
                if exit_code:
                    sys.exit(exit_code)
                return
            if for_database_host:
                from .database.commands import run_database_command  # noqa: PLC0415  # optional

                exit_code = run_database_command(self.cli_args, self._ports())
                if exit_code:
                    sys.exit(exit_code)
                return
            if for_manifest:
                from .manifest.commands import run_manifest_command  # noqa: PLC0415  # optional

                exit_code = run_manifest_command(self.cli_args, self._ports())
                if exit_code:
                    sys.exit(exit_code)
                return
            if for_modules:
                from .modules.commands import run_modules_command  # noqa: PLC0415  # optional

                exit_code = run_modules_command(self.cli_args, self._ports())
                if exit_code:
                    sys.exit(exit_code)
                return
            if for_run:
                from .recipes.commands import run_recipes_command  # noqa: PLC0415  # optional

                exit_code = run_recipes_command(self.cli_args, self._ports())
                if exit_code:
                    sys.exit(exit_code)
                return
            self._enforce_ci_explicit_mode()
            self.prepare_project_files()
            if for_image:
                from .image_layers import ensure_image_layer  # noqa: PLC0415  # optional

                ensure_image_layer(self._project_environment(), self.cli_args)
                return
            self._runtime().run_after_prepare()
        except OdpmError as exc:
            message = str(exc)
            if message:
                _logger.error("%s", message)
            sys.exit(exc.exit_code)

    def _enforce_ci_explicit_mode(self) -> None:
        ports = self.ports
        if ports is None:
            return
        scenario = ports.plan.host_ctx.policy.scenario
        if scenario != constants.CI_SCENARIO:
            return
        if cli_allows_ci_explicit_mode(self.cli_args):
            return
        message = _(
            "In the ci scenario use odpm prepare, odpm build, or odpm image "
            "(odpm up / bare compose up is not allowed)."
        )
        raise ConfigError(message)

    def _project_environment(self) -> CreateProjectEnvironment:
        if self.project_environment is None:
            raise RuntimeError("OdpmPipeline.setup() was not called")
        return self.project_environment

    def _system_checker(self) -> SystemChecker:
        if self.system_checker is None:
            raise RuntimeError("OdpmPipeline.setup() was not called")
        return self.system_checker
