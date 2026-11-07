"""Factories that build host ports / context from an internal assembled snapshot.

Campaign G: live in ``config/`` so ``host/`` does not import the assembler type
and ``host.context`` / ``host.ports`` no longer expose ``from_config`` /
``ports_from_config``.
"""

from __future__ import annotations

from typing import Any

from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..host.ports import BootstrapHandle, ComposePorts, PipelinePorts, PlanPorts, RuntimePorts
from ..host.runtime import HostRuntimeState
from ..project_env import CreateProjectEnvironment


def assemble_project(
    pd_manager,
    arguments: OdpmCliArgs,
    program_dir: str,
    user_env,
    *,
    secrets_fetch_session: object | None = None,
):
    """Construct the internal assembled snapshot (campaign H public entry)."""
    from .config import AssembledProject  # noqa: PLC0415  # cycle-safe

    return AssembledProject(
        pd_manager,
        arguments,
        program_dir,
        user_env,
        secrets_fetch_session=secrets_fetch_session,
    )


def host_context_from_assembled(
    assembled: Any,
    *,
    arguments: OdpmCliArgs | None = None,
) -> HostProjectContext:
    """Build :class:`HostProjectContext` from an internal assembled snapshot."""
    bootstrap = getattr(assembled, "bootstrap", None)
    manifest_view = bootstrap.manifest_view if bootstrap is not None else None
    repo_odpm_json = bootstrap.repo_odpm_json if bootstrap is not None else ""

    layout_default = getattr(
        getattr(assembled, "docker_layout", None),
        "docker_compose_command",
        "",
    )
    if not isinstance(layout_default, str):
        layout_default = ""
    runtime = getattr(assembled, "runtime", None)
    if isinstance(runtime, HostRuntimeState):
        docker_compose_command = runtime.resolved_docker_compose_command(
            layout_default
        )
    else:
        override = getattr(runtime, "docker_compose_command", None)
        docker_compose_command = (
            override if isinstance(override, str) else layout_default
        )

    return HostProjectContext(
        project_dir=assembled.project_dir,
        program_dir=assembled.program_dir,
        config_home_dir=assembled.config_home_dir,
        policy=assembled.policy,
        user_env=assembled.user_env,
        arguments=arguments if arguments is not None else assembled.arguments,
        user_settings=assembled.user_settings,
        project_settings=assembled.project_settings,
        docker_layout=assembled.docker_layout,
        addon_layout=assembled.addon_layout,
        docker_compose_command=docker_compose_command,
        manifest_view=manifest_view,
        repo_odpm_json=repo_odpm_json,
    )


def bootstrap_handle_from_assembled(assembled: Any) -> BootstrapHandle:
    """Wrap an assembled snapshot in :class:`BootstrapHandle`."""
    return BootstrapHandle(_assembled=assembled)


def ports_from_assembled(
    assembled: Any,
    project_env: CreateProjectEnvironment | None = None,
    args: OdpmCliArgs | None = None,
) -> PipelinePorts:
    """Build :class:`PipelinePorts` from an internal assembled snapshot."""
    resolved_args = args if args is not None else assembled.arguments
    env_bootstrap = (
        getattr(project_env, "bootstrap", None) if project_env is not None else None
    )
    bootstrap = (
        env_bootstrap
        if isinstance(env_bootstrap, BootstrapHandle)
        else bootstrap_handle_from_assembled(assembled)
    )
    resolved_env = (
        project_env
        if project_env is not None
        else CreateProjectEnvironment(bootstrap)
    )
    host_ctx = host_context_from_assembled(assembled, arguments=resolved_args)
    plan = PlanPorts(host_ctx=host_ctx, args=resolved_args, bootstrap=bootstrap)
    compose = ComposePorts(
        host_ctx=host_ctx,
        project_env=resolved_env,
        bootstrap=bootstrap,
    )
    runtime = RuntimePorts(
        host_ctx=host_ctx,
        args=resolved_args,
        project_env=resolved_env,
        bootstrap=bootstrap,
    )
    return PipelinePorts(plan=plan, compose=compose, runtime=runtime)
