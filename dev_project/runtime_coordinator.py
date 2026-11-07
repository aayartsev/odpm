"""Post-prepare runtime: CI image build, VS Code, compose up."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from . import host_summaries
from .database.adopt import adopt_database_baseline
from .database.resolve import ensure_no_blocking_database_drift
from .debugger.ide import ide_includes_pycharm, ide_includes_vscode
from .errors import ConfigError, PipelineError
from .extensions.context import ExtensionHostContext
from .extensions.hooks import run_lifecycle_hooks
from .host.cli.args import OdpmCliArgs
from .host.context import HostProjectContext
from .logging import get_module_logger
from .manifest.secrets_policy import ensure_secrets_requirements_met
from .project_env.debug_profile import write_debug_profile
from .project_env.services import (
    PycharmConfigurator,
    VscodeConfigurator,
)
from .runtime_backend import execute_launch_steps, get_runtime_backend
from .runtime_backend.compose import ComposeRuntimeBackend
from .translations import _

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

    @property
    def runtime_backend(self) -> ComposeRuntimeBackend:
        # Fresh adapter each access so host_ctx mirrors current config/args.
        return get_runtime_backend(
            host_ctx=self.host_ctx,
            config=self.config,
            project_env=self.project_env,
        )

    def handle_build_image(self) -> bool:
        """Run CI image build. Returns True when the pipeline should stop."""
        if not self.cli_args.build_image:
            return False
        if not self.host_ctx.policy.allow_build_image:
            message = _('odpm build is only allowed when ODPM_SCENARIO=ci in .env')
            _logger.error(message)
            raise PipelineError(message, exit_code=1)

        from .project_env.services import CiImageBuildService  # noqa: PLC0415  # optional

        CiImageBuildService(self.project_env).build_ci_image()
        return True

    def write_debug_profile(self) -> None:
        if not self.host_ctx.policy.include_debugpy:
            return
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
        return self.runtime_backend.build_compose_up_argv(
            force_recreate=force_recreate
        )

    def start_containers(self) -> None:
        """Thin facade for tests / pipeline: same registry as post-gate launch."""
        execute_launch_steps(self, force=True)

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
        adopt_database_baseline(self.config)
        ensure_no_blocking_database_drift(self.config, self.cli_args)

        manifest_view = self.config.bootstrap.manifest_view
        secrets_spec = (
            manifest_view.scenario_slice.secrets
            if manifest_view is not None and manifest_view.scenario_slice is not None
            else None
        )
        try:
            ensure_secrets_requirements_met(
                self.host_ctx.project_dir,
                secrets_spec,
                mount_secrets_from_host=self.host_ctx.policy.mount_runtime_secrets_from_host(),
                scenario=self.host_ctx.policy.scenario,
            )
        except ConfigError as exc:
            _logger.error(str(exc))
            raise PipelineError(str(exc), exit_code=1) from exc

        run_lifecycle_hooks(
            ExtensionHostContext.from_config(self.config),
            "pre_up",
            cwd=self.host_ctx.project_dir,
            env_resolver=self.config.env_resolver,
        )
        try:
            execute_launch_steps(self)
        except KeyboardInterrupt:
            host_summaries.log_control_c()
            sys.exit()
