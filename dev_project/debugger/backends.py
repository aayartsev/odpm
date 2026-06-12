"""Debugger backend registry (container exec + pip requirements)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .. import constants
from .constants import (
    DEBUGGER_BACKEND_DEBUGPY_LISTEN,
    DEBUGGER_DIRECTION_ATTACH,
    DEBUGGER_PROTOCOL_DEBUGPY,
)

DebuggerDirection = Literal["listen", "connect"]


class DebuggerBackend(Protocol):
    id: str
    direction: DebuggerDirection
    protocol: str

    def pip_requirement(self, python_version: str) -> str | None: ...

    @property
    def needs_compose_port_publish(self) -> bool: ...

    def wrap_exec_argv(
        self,
        venv_python: str,
        odoo_argv: list[str],
        *,
        listen_port: int,
    ) -> list[str]: ...


@dataclass(frozen=True)
class DebugpyListenBackend:
    id: str = DEBUGGER_BACKEND_DEBUGPY_LISTEN
    direction: DebuggerDirection = "listen"
    protocol: str = DEBUGGER_PROTOCOL_DEBUGPY

    def pip_requirement(self, python_version: str) -> str | None:
        return constants.DEBUGPY.get(python_version, constants.DEFAULT_DEBUGPY)

    @property
    def needs_compose_port_publish(self) -> bool:
        return True

    def wrap_exec_argv(
        self,
        venv_python: str,
        odoo_argv: list[str],
        *,
        listen_port: int,
    ) -> list[str]:
        exec_argv = [venv_python, "-u", "-m", "debugpy", "--listen", f"0.0.0.0:{listen_port}"]
        exec_argv.extend(odoo_argv)
        return exec_argv


DEBUGGER_BACKENDS: dict[str, DebuggerBackend] = {
    DEBUGGER_BACKEND_DEBUGPY_LISTEN: DebugpyListenBackend(),
}


def get_backend(backend_id: str) -> DebuggerBackend:
    try:
        return DEBUGGER_BACKENDS[backend_id]
    except KeyError as exc:
        raise ValueError(f"unknown debugger backend: {backend_id!r}") from exc
