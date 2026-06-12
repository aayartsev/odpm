"""Pluggable remote debugger backends for odpm developer scenario."""

from .backends import DEBUGGER_BACKENDS, DebuggerBackend, get_backend
from .constants import (
    DEBUGGER_BACKEND_DEBUGPY_LISTEN,
    DEFAULT_DEBUGGER_BACKEND,
    DEFAULT_ODPM_IDE,
)
from .env_parsing import (
    parse_debugger_backend,
    parse_debugger_connect_host,
    parse_debugger_suspend,
    parse_odpm_ide,
)
from .requirements import (
    is_debugger_requirement,
    is_debugpy_requirement,
    normalize_debugger_requirements,
)
from .ide import ide_includes_pycharm, ide_includes_vscode
from .resolve import resolve_debugger_backend

__all__ = [
    "DEBUGGER_BACKEND_DEBUGPY_LISTEN",
    "DEBUGGER_BACKENDS",
    "DEFAULT_DEBUGGER_BACKEND",
    "DEFAULT_ODPM_IDE",
    "DebuggerBackend",
    "get_backend",
    "ide_includes_pycharm",
    "ide_includes_vscode",
    "is_debugger_requirement",
    "is_debugpy_requirement",
    "normalize_debugger_requirements",
    "parse_debugger_backend",
    "parse_debugger_connect_host",
    "parse_debugger_suspend",
    "parse_odpm_ide",
    "resolve_debugger_backend",
]
