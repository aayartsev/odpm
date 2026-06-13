"""Resolve effective Odoo build date from CLI args or odpm.json."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Config


class OdooBuildDateResolver:
    def __init__(self, config: Config) -> None:
        self.config = config

    def get_effective_odoo_build_date(self) -> str:
        cli_date = getattr(self.config.arguments, "odoo_build_date", None)
        if cli_date:
            return cli_date.strip()
        return (self.config._raw_odpm_json.get("odoo_build_date") or "").strip()
