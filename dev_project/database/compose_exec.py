"""Run docker compose exec against the project postgres service."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from ..subprocess_runner import CommandResult, run_checked
from ..docker_capabilities import resolve_docker_capabilities

if TYPE_CHECKING:
    from ..config import Config


def _compose_argv(config: Config) -> list[str]:
    return shlex.split(config.docker_compose_command)


def postgres_service_name(config: Config) -> str:
    return config.user_env.postgres_service_name


def compose_exec(
    config: Config,
    service: str,
    *exec_args: str,
    user: str | None = None,
) -> CommandResult:
    argv = _compose_argv(config) + ["exec"]
    if user is not None:
        argv.extend(["-u", user])
    argv.extend(["-T", service, *exec_args])
    return run_checked(argv, cwd=config.project_dir)


def compose_run(
    config: Config,
    service: str,
    *run_args: str,
    user: str | None = None,
    input_text: str | None = None,
    entrypoint: str | None = None,
) -> CommandResult:
    argv = _compose_argv(config) + ["run", "--rm", "--no-deps"]
    if entrypoint is not None:
        argv.extend(["--entrypoint", entrypoint])
    if user is not None:
        argv.extend(["-u", user])
    argv.extend(["-T", service, *run_args])
    return run_checked(
        argv,
        cwd=config.project_dir,
        input_text=input_text,
    )


def compose_stop_service(config: Config, service: str) -> CommandResult:
    return run_checked(
        _compose_argv(config) + ["stop", service],
        cwd=config.project_dir,
    )


def compose_up_detached_argv(config: Config, service: str) -> list[str]:
    """Build ``compose up -d`` argv; append ``-y`` only when the CLI supports it."""
    capabilities = resolve_docker_capabilities(config)
    argv = _compose_argv(config) + ["up", "-d"]
    if capabilities.supports_compose_up_yes:
        argv.append("-y")
    argv.append(service)
    return argv


def compose_up_service_detached(config: Config, service: str) -> CommandResult:
    """Start one compose service detached; ``-y`` avoids Compose volume prompts when supported."""
    return run_checked(
        compose_up_detached_argv(config, service),
        cwd=config.project_dir,
    )


def postgres_container_id(config: Config) -> str | None:
    from ..compose.runtime import compose_service_container_id

    return compose_service_container_id(config, postgres_service_name(config))
