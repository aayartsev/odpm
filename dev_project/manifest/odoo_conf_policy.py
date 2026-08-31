"""Manifest odoo.conf option policy (stdlib-only).

ADR-022: global frozen keys apply in every scenario; ``db_*`` keys are
forbidden except in the effective ``ci`` slice.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .. import constants
from ..errors import ConfigError
from ..translations import _

ODOO_CONF_GLOBAL_FROZEN_KEYS = frozenset({
    "addons_path",
    "data_dir",
    "admin_passwd",
    "http_port",
})

ODOO_CONF_SCENARIO_FROZEN_KEYS = frozenset({
    "db_host",
    "db_port",
    "db_user",
    "db_password",
})

# Deprecated alias for docs / migration (union of global + scenario frozen).
ODOO_CONF_RESERVED_OPTION_KEYS = (
    ODOO_CONF_GLOBAL_FROZEN_KEYS | ODOO_CONF_SCENARIO_FROZEN_KEYS
)


def frozen_keys_for_scenario(scenario: str) -> frozenset[str]:
    """Return keys that must not appear in ``odoo_conf.options`` for *scenario*."""
    name = (scenario or "").strip() or constants.DEFAULT_ODPM_SCENARIO
    if name == constants.CI_SCENARIO:
        return ODOO_CONF_GLOBAL_FROZEN_KEYS
    return ODOO_CONF_GLOBAL_FROZEN_KEYS | ODOO_CONF_SCENARIO_FROZEN_KEYS


def manifest_ci_db_override(effective_odoo_conf: Mapping[str, Any] | None) -> bool:
    """True when effective ``odoo_conf.options`` contains any ``db_*`` key."""
    if not isinstance(effective_odoo_conf, Mapping):
        return False
    options = effective_odoo_conf.get("options")
    if not isinstance(options, Mapping):
        return False
    return any(key in ODOO_CONF_SCENARIO_FROZEN_KEYS for key in options)


def ci_manifest_db_override(
    manifest_view: object | None,
    *,
    is_ci: bool,
) -> bool:
    """Derived signal: CI scenario and effective options include any ``db_*``."""
    if not is_ci or manifest_view is None:
        return False
    return manifest_ci_db_override(getattr(manifest_view, "odoo_conf", None))


def validate_manifest_odoo_conf(
    odoo_conf: dict[str, Any] | Mapping[str, Any] | None,
    *,
    scenario: str,
) -> None:
    """Reject frozen Odoo option keys in a manifest ``odoo_conf`` fragment."""
    if not isinstance(odoo_conf, Mapping):
        return
    options = odoo_conf.get("options")
    if not isinstance(options, Mapping):
        return
    scenario_name = (scenario or "").strip() or constants.DEFAULT_ODPM_SCENARIO
    frozen = frozen_keys_for_scenario(scenario_name)
    for key in options:
        if key not in frozen:
            continue
        managed = ", ".join(sorted(frozen))
        raise ConfigError(
            _(
                'manifest odoo_conf.options.{KEY} cannot be overridden in '
                'scenario "{SCENARIO}".\n'
                "\n"
                "Keys managed by odpm in this scenario:\n"
                "  {KEYS}\n"
                "\n"
                'db_* overrides are allowed only in scenario "ci".'
            ).format(KEY=key, SCENARIO=scenario_name, KEYS=managed)
        )
