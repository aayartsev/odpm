"""Normalize init/update module lists from user settings and CLI."""

from __future__ import annotations

from typing import Any

from ... import constants
from ...errors import ConfigError
from ...translations import _


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


def normalize_cli_module_csv(raw: str) -> str:
    """Normalize a CLI ``-i``/``-u`` CSV; reject empty module lists."""
    beautified = beautify_module_list(raw)
    names = [name for name in beautified.split(",") if name]
    if not names:
        raise ConfigError(
            _(
                "-i/-u module list must contain at least one module name "
                "(comma-separated, e.g. sale,crm)"
            )
        )
    return ",".join(names)


def modules_csv_for_odoo_flag(
    cli_value: bool | str | None, settings_csv: str
) -> str | None:
    """Resolve modules for odoo-bin ``-i``/``-u`` (omit flag when ``None``)."""
    if cli_value is None or cli_value is False:
        return None
    if cli_value is True:
        return settings_csv if settings_csv else None
    if isinstance(cli_value, str):
        return normalize_cli_module_csv(cli_value)
    return None


def modules_csv_for_update_list(
    cli_u: bool | str | None, settings_csv: str
) -> str:
    """Resolve ``modules_to_update``: CLI ``-u CSV`` overrides settings."""
    if isinstance(cli_u, str):
        return normalize_cli_module_csv(cli_u)
    return settings_csv or ""
