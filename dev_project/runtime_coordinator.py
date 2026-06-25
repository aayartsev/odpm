"""Post-prepare runtime: CI image build, VS Code, compose up."""

from __future__ import annotations

import shlex
import sys
from typing import TYPE_CHECKING

from . import host_summaries
from .translations import _
from .host.context import HostProjectContext
from .compose.runtime import should_force_recreate_compose_for_host
from .errors import PipelineError
from .host.cli.args import OdpmCliArgs
from .logging import get_module_logger
from .debugger.ide import ide_includes_pycharm, ide_includes_vscode
from .project_env.services import PycharmConfigurator, VscodeConfigurator
from .subprocess_runner import run_logged

if TYPE_CHECKING:
    from .config import Config
    from .project_env import CreateProjectEnvironment

_logger = get_module_logger(__name__)


class RuntimeCoordinator:
    def __init__(
        self,
        cli_args: OdpmCliArgs,
        config: Config,
        project_env: CreateProjectEnvironment,
    ) -> None:
        self.cli_args = cli_args
        self.config = config
        self.project_env = project_env

    @property
    def host_ctx(self) -> HostProjectContext:
        return HostProjectContext.from_config(self.config, arguments=self.cli_args)

    def handle_build_image(self) -> bool:
        """Run CI image build. Returns True when the pipeline should stop."""
        if not self.cli_args.build_image:
            return False
        if not self.host_ctx.policy.allow_build_image:
            message = _('--build-image is only allowed when ODPM_SCENARIO=ci in .env')
            _logger.error(message)
            raise PipelineError(message, exit_code=1)
        from .project_env.services import CiImageBuildService

        CiImageBuildService(self.project_env).build_ci_image()
        return True

    def write_debug_profile(self) -> None:
        if not self.host_ctx.policy.include_debugpy:
            return
        from .project_env.debug_profile import write_debug_profile

        write_debug_profile(self.project_env)

    def configure_ide(self) -> None:
        if self.host_ctx.policy.skip_ide_config:
            return
        ide = self.host_ctx.user_env.odpm_ide
        if ide_includes_vscode(ide):
            vscode = VscodeConfigurator(self.project_env)
            vscode.update_vscode_debugger_launcher()
            vscode.generate_vscode_settings_json()
        if ide_includes_pycharm(ide):
            PycharmConfigurator(self.project_env).update_pycharm_run_configuration()

    def configure_vscode(self) -> None:
        self.configure_ide()

    def build_compose_up_argv(
        self, *, force_recreate: bool | None = None
    ) -> list[str]:
        if force_recreate is None:
            force_recreate = should_force_recreate_compose_for_host(self.host_ctx)
        argv = shlex.split(self.host_ctx.docker_compose_command) + ["up"]
        if self.config.no_log_prefix:
            argv.append("--no-log-prefix")
        argv.append("--abort-on-container-exit")
        if force_recreate:
            argv.append("--force-recreate")
        else:
            host_summaries.log_compose_stack_healthy()
        return argv

    def start_containers(self) -> None:
        from .project_env.services import BaseImageService

        BaseImageService(self.project_env).ensure_base_image()
        host_summaries.log_starting_containers(
            odoo_port=self.host_ctx.user_env.odoo_port,
        )
        returncode = run_logged(
            self.build_compose_up_argv(),
            cwd=self.host_ctx.project_dir,
        )
        if returncode != 0:
            if self.host_ctx.policy.report_compose_failure_on_host():
                host_summaries.log_compose_failed(returncode)
            raise PipelineError("", exit_code=returncode)

    def run_after_prepare(self) -> None:
        if self.handle_build_image():
            return
        self.write_debug_profile()
        self.configure_ide()
        if self.cli_args.update_lock:
            host_summaries.log_update_lock_skip()
            return
        if self.cli_args.skip_start:
            host_summaries.log_skip_start()
            return
        from .database.adopt import adopt_database_baseline
        from .database.resolve import ensure_no_blocking_database_drift

        adopt_database_baseline(self.config)
        ensure_no_blocking_database_drift(self.config, self.cli_args)
        from .extensions.hooks import run_lifecycle_hooks
        from .extensions.context import ExtensionHostContext

        run_lifecycle_hooks(
            ExtensionHostContext.from_config(self.config),
            "pre_up",
            cwd=self.host_ctx.project_dir,
            env_resolver=self.config.env_resolver,
        )
        try:
            self.start_containers()
        except KeyboardInterrupt:
            host_summaries.log_control_c()
            sys.exit()
