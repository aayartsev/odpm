"""Resolve debugger backend from container runtime config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .backends import DebuggerBackend, get_backend

if TYPE_CHECKING:
    from ..container_config import ContainerConfig, DebuggerSettings


def resolve_debugger_backend(
    config: ContainerConfig,
) -> DebuggerBackend | None:
    settings: DebuggerSettings | None = getattr(config, "debugger", None)
    if settings is None:
        return None
    return get_backend(settings.backend)
