"""Manifest odoo.conf option policy (stdlib-only)."""

from __future__ import annotations

from typing import Any

from ..errors import ConfigError
from ..translations import _

ODOO_CONF_RESERVED_OPTION_KEYS = frozenset({
    "addons_path",
    "data_dir",
    "db_host",
    "db_port",
    "db_user",
    "db_password",
    "admin_passwd",
    "http_port",
})


def validate_manifest_odoo_conf(raw: dict[str, Any]) -> None:
    """Reject reserved Odoo option keys in manifest ``odoo_conf``."""
    odoo_conf = raw.get("odoo_conf")
    if not isinstance(odoo_conf, dict):
        return
    options = odoo_conf.get("options")
    if not isinstance(options, dict):
        return
    for key in options:
        if key in ODOO_CONF_RESERVED_OPTION_KEYS:
            raise ConfigError(
                _(
                    "manifest odoo_conf.options.{KEY} is reserved; "
                    "odpm manages this option automatically"
                ).format(KEY=key)
            )
