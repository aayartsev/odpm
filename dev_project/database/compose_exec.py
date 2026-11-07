"""Run docker compose exec against the project postgres service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..subprocess_runner import CommandResult, run_checked
from ..docker_capabilities import resolve_docker_capabilities
from ..compose.runtime import compose_cli_argv, compose_service_container_id
from ..host.context import HostProjectContext

if TYPE_CHECKING:
    from ..host.ports import BootstrapHandle


def _host_ctx(bootstrap: BootstrapHandle) -> HostProjectContext:
    return bootstrap.host_context()


def _compose_argv(bootstrap: BootstrapHandle) -> list[str]:
    return compose_cli_argv(_host_ctx(bootstrap))


def postgres_service_name(bootstrap: BootstrapHandle) -> str:
    return bootstrap.user_env.postgres_service_name


def compose_exec(
    bootstrap: BootstrapHandle,
    service: str,
    *exec_args: str,
    user: str | None = None,
) -> CommandResult:
    argv = _compose_argv(bootstrap) + ["exec"]
    if user is not None:
        argv.extend(["-u", user])
    argv.extend(["-T", service, *exec_args])
    return run_checked(argv, cwd=_host_ctx(bootstrap).project_dir)


def compose_run(
    bootstrap: BootstrapHandle,
    service: str,
    *run_args: str,
    user: str | None = None,
    input_text: str | None = None,
    entrypoint: str | None = None,
) -> CommandResult:
    argv = _compose_argv(bootstrap) + ["run", "--rm", "--no-deps"]
    if entrypoint is not None:
        argv.extend(["--entrypoint", entrypoint])
    if user is not None:
        argv.extend(["-u", user])
    argv.extend(["-T", service, *run_args])
    return run_checked(
        argv,
        cwd=_host_ctx(bootstrap).project_dir,
        input_text=input_text,
    )


def compose_stop_service(bootstrap: BootstrapHandle, service: str) -> CommandResult:
    return run_checked(
        _compose_argv(bootstrap) + ["stop", service],
        cwd=_host_ctx(bootstrap).project_dir,
    )


def compose_up_detached_argv(bootstrap: BootstrapHandle, service: str) -> list[str]:
    """Build ``compose up -d`` argv; append ``-y`` only when the CLI supports it."""
    # Capabilities still take AssembledProject until campaign F.
    capabilities = resolve_docker_capabilities(bootstrap)
    argv = _compose_argv(bootstrap) + ["up", "-d"]
    if capabilities.supports_compose_up_yes:
        argv.append("-y")
    argv.append(service)
    return argv


def compose_up_service_detached(bootstrap: BootstrapHandle, service: str) -> CommandResult:
    """Start one compose service detached; ``-y`` avoids Compose volume prompts when supported."""
    return run_checked(
        compose_up_detached_argv(bootstrap, service),
        cwd=_host_ctx(bootstrap).project_dir,
    )


def postgres_container_id(bootstrap: BootstrapHandle) -> str | None:
    return compose_service_container_id(
        _host_ctx(bootstrap),
        postgres_service_name(bootstrap),
    )
