"""Debugger exec settings passed from ContainerConfig to backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import constants
from .constants import DEFAULT_DEBUGGER_CONNECT_HOST

if TYPE_CHECKING:
    from ..container_config import ContainerConfig


@dataclass(frozen=True)
class DebuggerExecSettings:
    port: int
    connect_host: str = DEFAULT_DEBUGGER_CONNECT_HOST
    suspend_on_connect: bool = False


def debugger_exec_settings_from_config(config: ContainerConfig) -> DebuggerExecSettings:
    settings = config.debugger
    if settings is None:
        return DebuggerExecSettings(port=constants.DEBUGGER_DEFAULT_PORT)
    return DebuggerExecSettings(
        port=settings.port,
        connect_host=settings.connect_host,
        suspend_on_connect=settings.suspend_on_connect,
    )
