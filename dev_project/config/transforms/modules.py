"""Normalize init/update module lists from user settings."""

from __future__ import annotations

from typing import Any

from ... import constants


def beautify_module_list(modules: Any) -> str:
    if not modules:
        return constants.DEFAULT_LIST_OF_MODULES
    if isinstance(modules, list):
        modules = ",".join(modules)
    if isinstance(modules, str):
        modules = modules.split(",")
        modules = [module.strip() for module in modules]
        modules = ",".join(modules)
    return modules
