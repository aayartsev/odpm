"""Host-side project context, runtime state, user environment, and CLI."""

import importlib

from .cli import OdpmCliArgs, arg_parser, parse_cli_args
from .context import HostProjectContext
from .runtime import HostRuntimeState
from .user_env import CreateUserEnvironment

__all__ = [
    "CreateUserEnvironment",
    "HostProjectContext",
    "HostRuntimeState",
    "OdpmCliArgs",
    "arg_parser",
    "parse_cli_args",
]

_HOST_SUBMODULES = frozenset(
    {
        "cli",
        "locale_bootstrap",
        "postgres_service_name",
        "ports",
        "user_env",
        "user_env_parse",
        "user_env_wizard",
    }
)


def __getattr__(name: str):
    if name in _HOST_SUBMODULES:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
