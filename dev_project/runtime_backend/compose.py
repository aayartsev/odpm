"""Docker Compose adapter for the runtime engine protocol."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from .. import host_summaries
from ..compose.runtime import (
    compose_project_cli_args,
    should_force_recreate_compose_for_host,
)
from ..errors import PipelineError
from ..host.ports import effective_odoo_port
from ..project_env.services import BaseImageService
from ..subprocess_runner import run_logged
from ..translations import _

if TYPE_CHECKING:
    from ..config import Config
    from ..host.context import HostProjectContext
    from ..project_env import CreateProjectEnvironment


class ComposeRuntimeBackend:
    """Compose-only stack launcher; owns ``docker compose up`` argv."""

    def __init__(
        self,
        *,
        host_ctx: HostProjectContext,
        config: Config,
        project_env: CreateProjectEnvironment,
    ) -> None:
        self.host_ctx = host_ctx
        self.config = config
        self.project_env = project_env

    def ensure_base_image(self) -> None:
        BaseImageService(self.project_env).ensure_base_image()

    def build_compose_up_argv(
        self, *, force_recreate: bool | None = None
    ) -> list[str]:
        if force_recreate is None:
            force_recreate = should_force_recreate_compose_for_host(self.host_ctx)
        argv = shlex.split(self.host_ctx.docker_compose_command)
        argv.extend(compose_project_cli_args(self.host_ctx.user_env))
        argv += ["up"]
        if self.config.no_log_prefix:
            argv.append("--no-log-prefix")
        argv.append("--abort-on-container-exit")
        if force_recreate:
            argv.append("--force-recreate")
        else:
            host_summaries.log_compose_stack_healthy()
        return argv

    def up(self) -> None:
        host_summaries.log_starting_containers(
            odoo_port=effective_odoo_port(self.host_ctx.user_env),
        )
        returncode = run_logged(
            self.build_compose_up_argv(),
            cwd=self.host_ctx.project_dir,
        )
        if returncode != 0:
            if self.host_ctx.policy.report_compose_failure_on_host():
                host_summaries.log_compose_failed(returncode)
            raise PipelineError("", exit_code=returncode)

    def down(self) -> None:
        raise PipelineError(
            _("Runtime engine method {METHOD!r} is not implemented for Compose").format(
                METHOD="down"
            )
        )

    def logs(self) -> None:
        raise PipelineError(
            _("Runtime engine method {METHOD!r} is not implemented for Compose").format(
                METHOD="logs"
            )
        )

    def exec(self) -> None:
        raise PipelineError(
            _("Runtime engine method {METHOD!r} is not implemented for Compose").format(
                METHOD="exec"
            )
        )
