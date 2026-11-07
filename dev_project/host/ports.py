"""Typed host ports between bootstrap :class:`Config` and plan/prepare/runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .cli.args import OdpmCliArgs
from .context import HostProjectContext

if TYPE_CHECKING:
    from ..config import Config
    from ..config.git_repos import GitRepoCoordinator
    from ..config.odoo_conf import OdooConfBuilder
    from ..config.transforms.env_substitution import EnvResolver
    from ..git.deps_lock_manager import DepsLockManager
    from ..manifest.reader import ManifestView
    from .runtime import HostRuntimeState
    from ..project_dir_manager import ProjectDirManager
from ..project_env import CreateProjectEnvironment
from ..secrets_providers.session import session_for_config


@dataclass(frozen=True)
class BootstrapHandle:
    """Mutable bootstrap hub for materialize / execute steps only.

    Plan and prepare *evaluate* must read :class:`HostProjectContext` and port
    slices. Execute may use ``config``, :meth:`git_repos`, and
    :meth:`new_lock_manager`, plus narrow accessors below (ADR-030).
    """

    config: Config

    @property
    def runtime(self) -> HostRuntimeState:
        return self.config.runtime

    @property
    def git_repos(self) -> GitRepoCoordinator:
        return self.config._git_repos

    @property
    def env_resolver(self) -> EnvResolver:
        return self.config.env_resolver

    @property
    def odoo_conf(self) -> OdooConfBuilder:
        return self.config._odoo_conf

    @property
    def pd_manager(self) -> ProjectDirManager:
        return self.config.pd_manager

    def new_lock_manager(self) -> DepsLockManager:
        from ..git.deps_lock_manager import DepsLockManager  # noqa: PLC0415  # cycle

        return DepsLockManager(self.config)

    def compute_venv_lock_hash(self) -> str:
        return self.config.compute_venv_lock_hash()

    def secrets_session(self):
        return session_for_config(self.config)

    def clear_runtime_config_preview_cache(self) -> None:
        from ..plan.runtime_preview import (  # noqa: PLC0415  # cycle
            clear_runtime_config_preview_cache as _clear,
        )

        _clear(self.config)

    @property
    def manifest_view(self) -> ManifestView | None:
        return self.config.bootstrap.manifest_view

    @property
    def repo_odpm_json(self) -> str:
        return self.config.bootstrap.repo_odpm_json


@dataclass(frozen=True)
class PlanPorts:
    """Read-only plan evaluation surface (paths, policy, CLI args)."""

    host_ctx: HostProjectContext
    args: OdpmCliArgs
    bootstrap: BootstrapHandle


@dataclass(frozen=True)
class ComposePorts:
    """Compose preview/generate surface bound to project environment."""

    host_ctx: HostProjectContext
    project_env: CreateProjectEnvironment
    bootstrap: BootstrapHandle


@dataclass(frozen=True)
class RuntimePorts:
    """Post-prepare runtime plan and coordinator surface."""

    host_ctx: HostProjectContext
    args: OdpmCliArgs
    project_env: CreateProjectEnvironment
    bootstrap: BootstrapHandle

    def debug_profile_needs_update(
        self, project_env: CreateProjectEnvironment | None = None
    ):
        from ..plan.debug_profile_preview import (  # noqa: PLC0415  # cycle
            debug_profile_needs_update as _needs,
        )

        return _needs(self.bootstrap.config, project_env)

    def vscode_settings_up_to_date(self) -> bool:
        from ..plan.compose_preview import (  # noqa: PLC0415  # cycle
            vscode_settings_up_to_date as _up_to_date,
        )

        return _up_to_date(self.bootstrap.config)

    def pycharm_run_config_up_to_date(
        self, project_env: CreateProjectEnvironment | None = None
    ) -> bool:
        from ..plan.pycharm_preview import (  # noqa: PLC0415  # cycle
            pycharm_run_config_up_to_date as _up_to_date,
        )

        return _up_to_date(self.bootstrap.config, project_env)

    def pycharm_run_config_description(self) -> str:
        from ..plan.pycharm_preview import (  # noqa: PLC0415  # cycle
            pycharm_run_config_description as _description,
        )

        return _description(self.bootstrap.config)


@dataclass(frozen=True)
class PipelinePorts:
    """Host pipeline ports created once in :meth:`OdpmPipeline.setup`."""

    plan: PlanPorts
    compose: ComposePorts
    runtime: RuntimePorts

    @property
    def bootstrap(self) -> BootstrapHandle:
        return self.plan.bootstrap

    @classmethod
    def from_setup(
        cls,
        config: Config,
        project_env: CreateProjectEnvironment,
        args: OdpmCliArgs,
    ) -> PipelinePorts:
        host_ctx = HostProjectContext.from_config(config, arguments=args)
        env_bootstrap = getattr(project_env, "bootstrap", None)
        bootstrap = (
            env_bootstrap
            if isinstance(env_bootstrap, BootstrapHandle)
            else BootstrapHandle(config=config)
        )
        plan = PlanPorts(host_ctx=host_ctx, args=args, bootstrap=bootstrap)
        compose = ComposePorts(
            host_ctx=host_ctx,
            project_env=project_env,
            bootstrap=bootstrap,
        )
        runtime = RuntimePorts(
            host_ctx=host_ctx,
            args=args,
            project_env=project_env,
            bootstrap=bootstrap,
        )
        return cls(plan=plan, compose=compose, runtime=runtime)


def ports_from_config(
    config: Config,
    project_env: CreateProjectEnvironment | None = None,
    args: OdpmCliArgs | None = None,
) -> PipelinePorts:
    """Build ports for tests and legacy call sites that still hold a bare Config."""

    resolved_args = args if args is not None else config.arguments
    resolved_env = (
        project_env
        if project_env is not None
        else CreateProjectEnvironment(BootstrapHandle(config=config))
    )
    return PipelinePorts.from_setup(config, resolved_env, resolved_args)


def _raw_user_port(user_env: object, attr: str, default: int) -> int:
    value = getattr(user_env, attr, None)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def _user_port_offset(user_env: object) -> int:
    value = getattr(user_env, "port_offset", 0)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def effective_odoo_port(user_env: object) -> int:
    from .. import constants  # noqa: PLC0415  # keep module import light
    from ..compose.ports import assert_host_port_in_range  # noqa: PLC0415  # cycle-safe

    raw = _raw_user_port(user_env, "odoo_port", constants.ODOO_DEFAULT_PORT)
    return assert_host_port_in_range(
        raw + _user_port_offset(user_env), context="ODOO_PORT + ODPM_PORT_OFFSET"
    )


def effective_postgres_port(user_env: object) -> int:
    from .. import constants  # noqa: PLC0415  # keep module import light
    from ..compose.ports import assert_host_port_in_range  # noqa: PLC0415  # cycle-safe

    raw = _raw_user_port(user_env, "postgres_port", constants.POSTGRES_DEFAULT_PORT)
    return assert_host_port_in_range(
        raw + _user_port_offset(user_env), context="POSTGRES_PORT + ODPM_PORT_OFFSET"
    )


def effective_debugger_port(user_env: object) -> int:
    from .. import constants  # noqa: PLC0415  # keep module import light
    from ..compose.ports import assert_host_port_in_range  # noqa: PLC0415  # cycle-safe

    raw = _raw_user_port(user_env, "debugger_port", constants.DEBUGGER_DEFAULT_PORT)
    return assert_host_port_in_range(
        raw + _user_port_offset(user_env), context="DEBUGGER_PORT + ODPM_PORT_OFFSET"
    )


def effective_gevent_port(user_env: object) -> int:
    from .. import constants  # noqa: PLC0415  # keep module import light
    from ..compose.ports import assert_host_port_in_range  # noqa: PLC0415  # cycle-safe

    raw = _raw_user_port(user_env, "gevent_port", constants.GEVENT_DEFAULT_PORT)
    return assert_host_port_in_range(
        raw + _user_port_offset(user_env), context="GEVENT_PORT + ODPM_PORT_OFFSET"
    )
