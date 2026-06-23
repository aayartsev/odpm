"""Typed host ports between bootstrap :class:`Config` and plan/prepare/runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .cli.args import OdpmCliArgs
from .context import HostProjectContext

if TYPE_CHECKING:
    from ..config import Config
    from ..config.git_repos import GitRepoCoordinator
    from ..git.deps_lock_manager import DepsLockManager
    from ..manifest.reader import ManifestView
    from ..project_env import CreateProjectEnvironment


@dataclass(frozen=True)
class BootstrapHandle:
    """Mutable bootstrap hub for materialize / execute steps only.

    Plan and prepare *evaluate* must read :class:`HostProjectContext` and port
    slices. Execute may use ``config``, :meth:`git_repos`, and
    :meth:`new_lock_manager`.
    """

    config: Config

    @property
    def git_repos(self) -> GitRepoCoordinator:
        return self.config._git_repos

    def new_lock_manager(self) -> DepsLockManager:
        from ..git.deps_lock_manager import DepsLockManager

        return DepsLockManager(self.config)

    def compute_venv_lock_hash(self) -> str:
        return self.config.compute_venv_lock_hash()

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
        bootstrap = BootstrapHandle(config=config)
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
    from ..project_env import CreateProjectEnvironment

    resolved_args = args if args is not None else config.arguments
    resolved_env = (
        project_env if project_env is not None else CreateProjectEnvironment(config)
    )
    return PipelinePorts.from_setup(config, resolved_env, resolved_args)
