"""Deprecated re-export. Prefer ``dev_project.project_env``."""

from __future__ import annotations

import warnings

warnings.warn(
    "dev_project.host_project_env is deprecated; import from dev_project.project_env instead",
    DeprecationWarning,
    stacklevel=1,
)

from .project_env import (
    CreateProjectEnvironment,
    DebuggerPathRecord,
    DebuggerUnit,
    MappedPath,
    SymlinksSources,
)

__all__ = [
    "CreateProjectEnvironment",
    "MappedPath",
    "SymlinksSources",
    "DebuggerPathRecord",
    "DebuggerUnit",
]
