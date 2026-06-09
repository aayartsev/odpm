"""Post-prepare runtime: CI image build, VS Code, compose up."""

from __future__ import annotations

import shlex
import sys
from typing import TYPE_CHECKING

from . import host_summaries
from .translations import _
from .compose.runtime import should_force_recreate_compose
from .errors import PipelineError
from .host.cli.args import OdpmCliArgs
from .logging import get_module_logger
from .project_env.services import VscodeConfigurator
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

    def handle_build_image(self) -> bool:
        """Run CI image build. Returns True when the pipeline should stop."""
        if not self.cli_args.build_image:
            return False
        if not self.config.policy.allow_build_image:
            message = _('--build-image is only allowed when ODPM_SCENARIO=ci in .env')
            _logger.error(message)
            raise PipelineError(message, exit_code=1)
        from .project_env.services import CiImageBuildService

        CiImageBuildService(self.project_env).build_ci_image()
        return True

    def configure_vscode(self) -> None:
        if self.config.policy.skip_vscode:
            return
        vscode = VscodeConfigurator(self.project_env)
        vscode.update_vscode_debugger_launcher()
        vscode.generate_vscode_settings_json()

    def build_compose_up_argv(
        self, *, force_recreate: bool | None = None
    ) -> list[str]:
        if force_recreate is None:
            force_recreate = should_force_recreate_compose(self.config)
        argv = shlex.split(self.config.docker_compose_command) + ["up"]
        if self.config.no_log_prefix:
            argv.append("--no-log-prefix")
        argv.append("--abort-on-container-exit")
        if force_recreate:
            argv.append("--force-recreate")
        else:
            host_summaries.log_compose_stack_healthy()
        return argv

    def start_containers(self) -> None:
        host_summaries.log_starting_containers(
            odoo_port=self.config.user_env.odoo_port,
        )
        returncode = run_logged(
            self.build_compose_up_argv(),
            cwd=self.config.project_dir,
        )
        if returncode != 0:
            host_summaries.log_compose_failed(returncode)
            message = _(host_summaries.MSG_COMPOSE_FAILED).format(EXIT_CODE=returncode)
            raise PipelineError(message, exit_code=returncode)

    def run_after_prepare(self) -> None:
        if self.handle_build_image():
            return
        self.configure_vscode()
        if self.cli_args.update_lock:
            host_summaries.log_update_lock_skip()
            return
        if self.cli_args.skip_start:
            host_summaries.log_skip_start()
            return
        try:
            self.start_containers()
        except KeyboardInterrupt:
            host_summaries.log_control_c()
            sys.exit()
