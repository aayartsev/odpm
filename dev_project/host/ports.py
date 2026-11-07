"""Typed host ports between bootstrap :class:`AssembledProject` and plan/prepare/runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .cli.args import OdpmCliArgs
from .context import HostProjectContext

if TYPE_CHECKING:
    from ..config.git_repos import GitRepoCoordinator
    from ..config.odoo_conf import OdooConfBuilder
    from ..config.transforms.env_substitution import EnvResolver
    from ..dependency_resolver import NestedOdpmFragment
    from ..git import HandleOdooProjectLink
    from ..git.deps_lock_manager import DepsLockManager
    from ..manifest.reader import ManifestView
    from .runtime import HostRuntimeState
    from ..project_dir_manager import ProjectDirManager
from ..project_env import CreateProjectEnvironment
from ..secrets_providers.session import session_for_config


@dataclass
class BootstrapHandle:
    """Mutable bootstrap hub for materialize / execute steps only.

    Plan and prepare *evaluate* must read :class:`HostProjectContext` and port
    slices. Execute may use :meth:`git_repos`, :meth:`new_lock_manager`, and
    narrow accessors below (ADR-030). The assembled snapshot is private
    (``_assembled``); there is no public ``.config``.

    Not frozen: workspace accessors need property setters that mutate
    ``_assembled`` (frozen dataclasses block ``handle.field = …`` even for
    properties). Do not rebind ``_assembled`` after construction.
    """

    _assembled: object

    @property
    def runtime(self) -> HostRuntimeState:
        return self._assembled.runtime

    @property
    def git_repos(self) -> GitRepoCoordinator:
        return self._assembled._git_repos

    @property
    def env_resolver(self) -> EnvResolver:
        return self._assembled.env_resolver

    @property
    def odoo_conf(self) -> OdooConfBuilder:
        return self._assembled._odoo_conf

    @property
    def pd_manager(self) -> ProjectDirManager:
        return self._assembled.pd_manager

    def new_lock_manager(self) -> DepsLockManager:
        from ..git.deps_lock_manager import DepsLockManager  # noqa: PLC0415  # cycle

        return DepsLockManager(self)

    def compute_venv_lock_hash(self) -> str:
        return self._assembled.compute_venv_lock_hash()

    def write_runtime_config(self) -> str:
        from ..config.payload import write_runtime_config  # noqa: PLC0415  # cycle

        return write_runtime_config(self._assembled)

    def write_runtime_config_to_path(self, path: str) -> str:
        from ..config.payload import (  # noqa: PLC0415  # cycle
            write_runtime_config_to_path,
        )

        return write_runtime_config_to_path(self._assembled, path)

    def runtime_config_json_bytes(self) -> bytes:
        from ..config.payload import config_to_json  # noqa: PLC0415  # cycle

        return config_to_json(self._assembled)

    def to_container_config(self):
        from ..container_config import ContainerConfig  # noqa: PLC0415  # cycle

        return ContainerConfig.from_odpm_config(self._assembled)

    def handle_git_link(
        self,
        gitlink: str,
        system_type: Literal["developing", "platform", "standart"] = "standart",
        *,
        materialize: bool = False,
    ) -> HandleOdooProjectLink:
        # Match historic call shape (omit default system_type).
        if system_type == "standart":
            return self.git_repos.handle_git_link(gitlink, materialize=materialize)
        return self.git_repos.handle_git_link(
            gitlink,
            system_type=system_type,
            materialize=materialize,
        )

    def ensure_git_repo_symlink(
        self,
        target_path: str,
        *,
        scope: Literal["project", "dependency"] = "project",
    ) -> None:
        from ..symlinks import ensure_git_repo_symlink  # noqa: PLC0415  # cycle

        ensure_git_repo_symlink(self, target_path, scope=scope)

    def ensure_developing_repo_symlinks(self) -> None:
        from ..symlinks import ensure_developing_repo_symlinks  # noqa: PLC0415  # cycle

        ensure_developing_repo_symlinks(self)

    def apply_nested_compatibility(
        self,
        nested_fragments: list[NestedOdpmFragment] | None = None,
    ) -> None:
        from ..config.nested_compatibility import (  # noqa: PLC0415  # cycle
            collect_nested_compatibility_issues,
        )
        from ..errors import PipelineError  # noqa: PLC0415  # cycle
        from ..logging import get_module_logger  # noqa: PLC0415  # cycle

        fragments = list(nested_fragments or [])
        logger = get_module_logger(__name__)
        for message in collect_nested_compatibility_issues(
            self.project_settings.odoo_version,
            self.project_settings.python_version,
            fragments,
        ):
            if self.policy.is_ci():
                logger.error(message)
                raise PipelineError(message, exit_code=1)
            logger.warning(message)

    def generate_odoo_conf_docker_data(self) -> None:
        self.odoo_conf.generate_odoo_conf_docker_data()

    @property
    def developing_project(self):
        return self._assembled.developing_project

    @developing_project.setter
    def developing_project(self, value) -> None:
        self._assembled.developing_project = value

    @property
    def odoo_platform_project(self):
        return self._assembled.odoo_platform_project

    @odoo_platform_project.setter
    def odoo_platform_project(self, value) -> None:
        self._assembled.odoo_platform_project = value

    @property
    def odoo_src_dir(self) -> str:
        return self._assembled.odoo_src_dir

    @odoo_src_dir.setter
    def odoo_src_dir(self, value: str) -> None:
        self._assembled.odoo_src_dir = value

    @property
    def developing_project_dir_path(self) -> str:
        return self._assembled.developing_project_dir_path

    @developing_project_dir_path.setter
    def developing_project_dir_path(self, value: str) -> None:
        self._assembled.developing_project_dir_path = value



    @property
    def config_home_dir(self) -> str:
        return self._assembled.config_home_dir

    def check_project_for_subprojects(self, *args, **kwargs):
        return self._assembled.check_project_for_subprojects(*args, **kwargs)

    @property
    def bootstrap_state(self):
        return self._assembled.bootstrap


    @property
    def user_settings(self):
        return self._assembled.user_settings

    @property
    def addon_layout(self):
        return self._assembled.addon_layout

    def bind_env_resolver_with_secrets(self, project_dir: str) -> None:
        from ..config.transforms.env_substitution import with_secrets  # noqa: PLC0415
        from ..config.transforms.secret_refs import load_secrets_map  # noqa: PLC0415

        self._assembled._env_resolver = with_secrets(
            self._assembled.env_resolver,
            load_secrets_map(project_dir),
        )

    def reload_manifest_view_from_source_raw(self) -> None:
        from ..manifest.reader import load_manifest  # noqa: PLC0415

        view = self._assembled.bootstrap.manifest_view
        source_raw = getattr(view, "source_raw", None) if view is not None else None
        if not isinstance(source_raw, dict) or not source_raw:
            return
        scenario = getattr(self._assembled.user_env, "odpm_scenario", None)
        self._assembled.bootstrap.manifest_view = load_manifest(
            dict(source_raw),
            env_resolver=self._assembled.env_resolver,
            active_scenario=scenario,
        )

    def host_context(self, *, arguments: OdpmCliArgs | None = None) -> HostProjectContext:
        from ..config.assembly import host_context_from_assembled  # noqa: PLC0415

        return host_context_from_assembled(self._assembled, arguments=arguments)

    @property
    def user_env(self):
        return self._assembled.user_env

    @property
    def project_settings(self):
        return self._assembled.project_settings

    @property
    def docker_layout(self):
        return self._assembled.docker_layout

    @property
    def policy(self):
        return self._assembled.policy

    @property
    def arguments(self) -> OdpmCliArgs:
        return self._assembled.arguments

    @property
    def project_dir(self) -> str:
        return self._assembled.project_dir

    @property
    def program_dir(self) -> str:
        return self._assembled.program_dir

    @property
    def dockerfile_path(self) -> str:
        return self._assembled.dockerfile_path

    @dockerfile_path.setter
    def dockerfile_path(self, value: str) -> None:
        self._assembled.dockerfile_path = value

    def skip_git_update(self) -> bool:
        return self._assembled.skip_git_update()

    def seed_dependency_urls(self):
        return self._assembled.seed_dependency_urls()

    @property
    def postgres_data_local_storage(self) -> str:
        return self._assembled.postgres_data_local_storage

    @property
    def service_source_paths(self) -> dict:
        return getattr(self._assembled.bootstrap, "service_source_paths", {}) or {}

    @service_source_paths.setter
    def service_source_paths(self, value: dict) -> None:
        self._assembled.bootstrap.service_source_paths = dict(value)

    @property
    def raw_user_settings(self) -> dict:
        return dict(self._assembled.bootstrap.raw_user_settings or {})

    def ensure_secrets_source(self, raw, *, phase: str = "prepare"):
        from ..secrets_providers.fetch import (  # noqa: PLC0415  # cycle
            ensure_secrets_source_for_config,
        )

        return ensure_secrets_source_for_config(self._assembled, raw=raw, phase=phase)

    def resolve_base_image_ref(self, *, registry: str | None = None) -> str:
        from ..config.paths import ConfigPaths  # noqa: PLC0415  # cycle

        return ConfigPaths(self._assembled).resolve_base_image_ref(registry=registry)

    def set_env_resolver(self, resolver) -> None:
        self._assembled._env_resolver = resolver

    def set_manifest_view(self, view) -> None:
        self._assembled.bootstrap.manifest_view = view

    def secrets_session(self):
        return session_for_config(self._assembled)

    def clear_runtime_config_preview_cache(self) -> None:
        from ..plan.runtime_preview import (  # noqa: PLC0415  # cycle
            clear_runtime_config_preview_cache as _clear,
        )

        _clear(self)

    def ensure_docker_capabilities(self, *, run_checked=None):
        from ..docker_capabilities import (  # noqa: PLC0415  # cycle
            ensure_config_docker_capabilities,
        )

        return ensure_config_docker_capabilities(self, run_checked=run_checked)

    @property
    def manifest_view(self) -> ManifestView | None:
        return self._assembled.bootstrap.manifest_view

    @property
    def repo_odpm_json(self) -> str:
        # Prefer bootstrap-state path (real AssembledProject + pipeline_ports tests); fall
        # back to top-level AssembledProject shim / MagicMock ``config.repo_odpm_json``.
        boot = getattr(self._assembled, "bootstrap", None)
        nested = getattr(boot, "repo_odpm_json", None) if boot is not None else None
        if isinstance(nested, str):
            return nested
        top = getattr(self._assembled, "repo_odpm_json", None)
        return top if isinstance(top, str) else ""

    @property
    def project_name(self) -> str:
        return str(getattr(self._assembled, "project_name", "") or "")


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

        return _needs(self.host_ctx, project_env)

    def vscode_settings_up_to_date(self) -> bool:
        from ..plan.compose_preview import (  # noqa: PLC0415  # cycle
            vscode_settings_up_to_date as _up_to_date,
        )

        return _up_to_date(self.host_ctx)

    def pycharm_run_config_up_to_date(
        self, project_env: CreateProjectEnvironment | None = None
    ) -> bool:
        from ..plan.pycharm_preview import (  # noqa: PLC0415  # cycle
            pycharm_run_config_up_to_date as _up_to_date,
        )

        return _up_to_date(self.host_ctx, project_env)

    def pycharm_run_config_description(self) -> str:
        from ..plan.pycharm_preview import (  # noqa: PLC0415  # cycle
            pycharm_run_config_description as _description,
        )

        return _description(self.host_ctx)


@dataclass(frozen=True)
class PipelinePorts:
    """Host pipeline ports created once in :meth:`OdpmPipeline.setup`."""

    plan: PlanPorts
    compose: ComposePorts
    runtime: RuntimePorts

    @property
    def bootstrap(self) -> BootstrapHandle:
        return self.plan.bootstrap



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
