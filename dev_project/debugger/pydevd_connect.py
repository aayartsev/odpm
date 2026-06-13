"""pydevd_connect backend: container connects to PyCharm Debug Server on the host."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .. import constants
from .constants import (
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
    DEBUGGER_PROTOCOL_PYDEVD,
)
from .exec_settings import DebuggerExecSettings

DebuggerDirection = Literal["listen", "connect"]


@dataclass(frozen=True)
class PydevdConnectBackend:
    id: str = DEBUGGER_BACKEND_PYDEVD_CONNECT
    direction: DebuggerDirection = "connect"
    protocol: str = DEBUGGER_PROTOCOL_PYDEVD

    def pip_requirement(self, python_version: str) -> str | None:
        return constants.PYDEVD_PYCHARM.get(
            python_version,
            constants.DEFAULT_PYDEVD_PYCHARM,
        )

    @property
    def needs_compose_port_publish(self) -> bool:
        return False

    def wrap_exec_argv(
        self,
        venv_python: str,
        odoo_argv: list[str],
        *,
        settings: DebuggerExecSettings,
    ) -> list[str]:
        del settings
        return [
            venv_python,
            "-u",
            "-m",
            constants.RUN_WITH_PYDEVD_ENTRYPOINT,
            "--",
            *odoo_argv,
        ]
