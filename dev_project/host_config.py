"""Deprecated re-export. Prefer ``dev_project.config``."""

from __future__ import annotations

import warnings

warnings.warn(
    "dev_project.host_config is deprecated; import from dev_project.config instead",
    DeprecationWarning,
    stacklevel=1,
)

from .config import (
    Config,
    ConfigToJson,
    DbCreationData,
    OdpmJson,
    SubProject,
    UserSettingsJson,
    compute_venv_lock_hash,
    config_to_json,
)

__all__ = [
    "Config",
    "ConfigToJson",
    "DbCreationData",
    "OdpmJson",
    "SubProject",
    "UserSettingsJson",
    "compute_venv_lock_hash",
    "config_to_json",
]
