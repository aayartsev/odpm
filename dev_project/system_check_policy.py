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
        check_system = bool(getattr(config, "check_system", True))
        policy = getattr(config, "policy", None)
        is_developer = policy.is_developer() if policy is not None else False
        return cls(
            beginner_git=check_system,
            beginner_docker=check_system,
            developer_port_release=is_developer,
            compose_validate=True,
            file_system_on_init=True,
        )
