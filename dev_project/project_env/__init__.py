"""Project environment helpers (templates, links, compose wiring).

``CreateProjectEnvironment`` loads lazily so transforms such as
``config.transforms.secret_refs`` can import ``project_env.secrets`` without a
cycle through this package ``__init__``.
"""

from __future__ import annotations

import importlib
from typing import Any

from ..symlinks import SymlinksSources
from .types import (
    DebuggerPathRecord,
    DebuggerUnit,
    MappedPath,
)

__all__ = [
    "CreateProjectEnvironment",
    "MappedPath",
    "SymlinksSources",
    "DebuggerPathRecord",
    "DebuggerUnit",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "CreateProjectEnvironment": (".environment", "CreateProjectEnvironment"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is not None:
        module_name, attr_name = target
        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)
    try:
        return importlib.import_module(f".{name}", __name__)
    except ModuleNotFoundError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(_LAZY_EXPORTS))
