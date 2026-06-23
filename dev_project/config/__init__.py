"""Host and container configuration package."""

import importlib

from .config import Config
from .payload import compute_extras_stamp, compute_venv_lock_hash, config_to_json
from .state import DockerLayoutState, ProjectSettingsState, UserSettingsState
from .types import (
    DbCreationData,
    OdpmJson,
    SubProject,
    UserSettingsJson,
)

__all__ = [
    "Config",
    "DbCreationData",
    "DockerLayoutState",
    "OdpmJson",
    "ProjectSettingsState",
    "SubProject",
    "UserSettingsJson",
    "UserSettingsState",
    "compute_extras_stamp",
    "compute_venv_lock_hash",
    "config_to_json",
]

_CONFIG_SUBMODULES = frozenset(
    {
        "artifacts",
        "bootstrap",
        "bootstrap_context",
        "bootstrap_phases",
        "config",
        "defaults",
        "git_repos",
        "layout",
        "manifests",
        "nested_compatibility",
        "odoo_conf",
        "paths",
        "payload",
        "runtime_facade",
        "transforms",
    }
)


def __getattr__(name: str):
    if name in _CONFIG_SUBMODULES:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
