"""Explicit gating matrix for host system checks and prepare steps."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from . import constants

if TYPE_CHECKING:
    from .config import Config
    from .host.cli.args import OdpmCliArgs


def _truthy_skip_start(arguments: OdpmCliArgs | None) -> bool:
    if arguments is None:
        return False
    return bool(arguments.skip_start)


def is_ci_prepare_only(arguments: OdpmCliArgs | None) -> bool:
    """Return True when CLI is prepare/build-only (no compose up)."""
    if arguments is None:
        return False
    return bool(
        _truthy_skip_start(arguments)
        or arguments.build_image
        or arguments.update_lock
        or arguments.sync_manifest_locks
        or arguments.init
    )


def cli_allows_ci_explicit_mode(arguments: OdpmCliArgs | None) -> bool:
    """Allowlist for bare ``odpm`` under ``ODPM_SCENARIO=ci`` (ADR-017)."""
    if arguments is None:
        return False
    if (
        _truthy_skip_start(arguments)
        or arguments.build_image
        or arguments.plan
        or arguments.update_lock
        or arguments.sync_manifest_locks
        or arguments.version
    ):
        return True
    if arguments.init:
        return True
    if arguments.command in {"plan", "database", "manifest"}:
        return True
    if arguments.database_subcommand is not None:
        return True
    if arguments.manifest_subcommand is not None:
        return True
    return False


def merged_environ_for_resolve(
    dotenv: Mapping[str, str] | None = None,
    *,
    process_environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Merge layered dotenv with process env (process wins)."""
    merged = dict(dotenv or {})
    source = process_environ if process_environ is not None else os.environ
    merged.update({key: str(value) for key, value in source.items()})
    return merged


def environ_from_config(config: Any) -> dict[str, str]:
    """Build resolve environ from ``Config`` / user_env dotenv + process env."""
    dotenv: Mapping[str, str] = {}
    user_env = getattr(config, "user_env", None)
    if user_env is not None and hasattr(user_env, "project_dotenv_dict"):
        maybe = user_env.project_dotenv_dict()
        if isinstance(maybe, dict):
            dotenv = maybe
    return merged_environ_for_resolve(dotenv)


def environ_from_host_context(host_ctx: Any) -> dict[str, str]:
    user_env = getattr(host_ctx, "user_env", None)
    dotenv: Mapping[str, str] = {}
    if user_env is not None and hasattr(user_env, "project_dotenv_dict"):
        maybe = user_env.project_dotenv_dict()
        if isinstance(maybe, dict):
            dotenv = maybe
    return merged_environ_for_resolve(dotenv)


@dataclass(frozen=True)
class SystemCheckPolicy:
    """Which host checks run for a given config and scenario."""

    beginner_git: bool
    beginner_docker: bool
    developer_port_release: bool
    compose_validate: bool
    file_system_on_init: bool
    skip_docker_daemon: bool = False
    skip_compose_cli_probe: bool = False
    skip_ensure_base_local: bool = False
    relaxed_file_system: bool = False
    require_ci_explicit_mode: bool = False

    @classmethod
    def from_config(cls, config: Config) -> SystemCheckPolicy:
        check_system = cls._check_system_enabled(config)
        policy = getattr(config, "policy", None)
        scenario = getattr(policy, "scenario", None) if policy is not None else None
        is_developer = scenario == constants.DEVELOPER_SCENARIO
        is_ci = scenario == constants.CI_SCENARIO
        arguments = getattr(config, "arguments", None)
        environ = environ_from_config(config)
        return cls._build(
            check_system=check_system,
            is_developer=is_developer,
            is_ci=is_ci,
            arguments=arguments,
            environ=environ,
        )

    @classmethod
    def from_host_context(cls, host_ctx) -> SystemCheckPolicy:
        check_system = bool(host_ctx.user_settings.check_system)
        arguments = getattr(host_ctx, "arguments", None)
        environ = environ_from_host_context(host_ctx)
        scenario = getattr(getattr(host_ctx, "policy", None), "scenario", None)
        return cls._build(
            check_system=check_system,
            is_developer=scenario == constants.DEVELOPER_SCENARIO,
            is_ci=scenario == constants.CI_SCENARIO,
            arguments=arguments,
            environ=environ,
        )

    @classmethod
    def _build(
        cls,
        *,
        check_system: bool,
        is_developer: bool,
        is_ci: bool,
        arguments: OdpmCliArgs | None,
        environ: Mapping[str, str],
    ) -> SystemCheckPolicy:
        from .host.cli.args import OdpmCliArgs
        from .project_env.image_build.resolve import resolve_ci_image_builder

        builder = resolve_ci_image_builder(arguments, environ=environ)
        raw_mode = environ.get(constants.ODPM_KANIKO_EXECUTOR_MODE_ENV, "")
        if not isinstance(raw_mode, str):
            raw_mode = ""
        raw_mode = raw_mode.strip().lower()
        kaniko_mode = raw_mode or constants.KANIKO_EXECUTOR_MODE_DOCKER_RUN
        if arguments is not None and isinstance(arguments, OdpmCliArgs):
            prepare_only = is_ci_prepare_only(arguments)
        else:
            prepare_only = False
        kaniko_direct = (
            builder == constants.CI_IMAGE_BUILDER_KANIKO
            and kaniko_mode == constants.KANIKO_EXECUTOR_MODE_DIRECT
        )
        skip_docker_daemon = bool(is_ci and kaniko_direct and prepare_only)
        skip_compose_cli_probe = skip_docker_daemon
        skip_ensure_base_local = bool(
            is_ci and builder == constants.CI_IMAGE_BUILDER_KANIKO
        )
        relaxed_file_system = bool(is_ci and prepare_only)
        return cls(
            beginner_git=check_system,
            beginner_docker=check_system,
            developer_port_release=is_developer,
            compose_validate=True,
            file_system_on_init=True,
            skip_docker_daemon=skip_docker_daemon,
            skip_compose_cli_probe=skip_compose_cli_probe,
            skip_ensure_base_local=skip_ensure_base_local,
            relaxed_file_system=relaxed_file_system,
            require_ci_explicit_mode=is_ci,
        )

    @staticmethod
    def _check_system_enabled(config) -> bool:
        user_settings = getattr(config, "user_settings", None)
        if user_settings is not None and hasattr(user_settings, "check_system"):
            return bool(user_settings.check_system)
        return bool(getattr(config, "check_system", True))
