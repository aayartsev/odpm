"""Explicit gating matrix for host system checks and prepare steps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config


@dataclass(frozen=True)
class SystemCheckPolicy:
    """Which host checks run for a given config and scenario."""

    beginner_git: bool
    beginner_docker: bool
    developer_port_release: bool
    compose_validate: bool
    file_system_on_init: bool

    @classmethod
    def from_config(cls, config: Config) -> SystemCheckPolicy:
        check_system = cls._check_system_enabled(config)
        policy = getattr(config, "policy", None)
        is_developer = policy.is_developer() if policy is not None else False
        return cls(
            beginner_git=check_system,
            beginner_docker=check_system,
            developer_port_release=is_developer,
            compose_validate=True,
            file_system_on_init=True,
        )

    @staticmethod
    def _check_system_enabled(config) -> bool:
        user_settings = getattr(config, "user_settings", None)
        if user_settings is not None and hasattr(user_settings, "check_system"):
            return bool(user_settings.check_system)
        return bool(getattr(config, "check_system", True))

    @classmethod
    def from_host_context(cls, host_ctx) -> SystemCheckPolicy:
        check_system = bool(host_ctx.user_settings.check_system)
        return cls(
            beginner_git=check_system,
            beginner_docker=check_system,
            developer_port_release=host_ctx.policy.is_developer(),
            compose_validate=True,
            file_system_on_init=True,
        )
