"""Host and container configuration package.

Leaf exports used inside the container (``payload`` stamps/hashes and
``types``) load eagerly. ``Config`` and settings slices load lazily so
``from dev_project.config.payload import …`` does not pull host-only deps
such as ``jsonschema`` (golden-path / ``check_virtualenv``).
"""

from __future__ import annotations

import importlib
from typing import Any

from .payload import (
    compute_extras_stamp,
    compute_odoo_requirements_hash,
    compute_venv_lock_hash,
    config_to_json,
)
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
    "compute_odoo_requirements_hash",
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
        "state",
        "transforms",
    }
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "Config": (".config", "Config"),
    "DockerLayoutState": (".state", "DockerLayoutState"),
    "ProjectSettingsState": (".state", "ProjectSettingsState"),
    "UserSettingsState": (".state", "UserSettingsState"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is not None:
        module_name, attr_name = target
        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)
    if name in _CONFIG_SUBMODULES:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(_LAZY_EXPORTS) | set(_CONFIG_SUBMODULES))
