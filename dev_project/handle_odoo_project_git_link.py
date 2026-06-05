"""Deprecated re-export. Prefer ``dev_project.git``."""

from __future__ import annotations

import warnings

warnings.warn(
    "dev_project.handle_odoo_project_git_link is deprecated; import from dev_project.git instead",
    DeprecationWarning,
    stacklevel=1,
)

from .git import (
    FILE_SYSTEM_MARKER,
    GIT_MARKER,
    HTTP_MARKER,
    SSH_MARKER,
    HandleOdooProjectLink,
    OdooProjectData,
)

__all__ = [
    "HandleOdooProjectLink",
    "OdooProjectData",
    "HTTP_MARKER",
    "GIT_MARKER",
    "SSH_MARKER",
    "FILE_SYSTEM_MARKER",
]
