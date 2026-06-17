"""Database drift preview for odpm plan warnings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..database.drift import (
    DatabaseDrift,
    detect_database_drift_for_config,
    has_blocking_database_drift,
    meaningful_database_drifts,
)
from ..translations import _

if TYPE_CHECKING:
    from ..config import Config

_DATABASE_DRIFT_MESSAGES = {
    "first_run": _(
        "No database last_run snapshot yet; settings will be recorded after a successful start."
    ),
    "service_name": _(
        "PostgreSQL compose service changed: {PREVIOUS} -> {CURRENT}."
    ),
    "db_host_mismatch": _(
        "odoo.conf db_host ({CURRENT}) does not match postgres service name ({PREVIOUS})."
    ),
    "host_port": _(
        "PostgreSQL host port changed: {PREVIOUS} -> {CURRENT}."
    ),
    "data_path": _(
        "PostgreSQL data directory changed: {PREVIOUS} -> {CURRENT}."
    ),
    "postgres_major": _(
        "PostgreSQL image version changed: {PREVIOUS} -> {CURRENT}."
    ),
    "odpm_scenario": _(
        "ODPM scenario changed: {PREVIOUS} -> {CURRENT}."
    ),
    "data_dir_empty_changed": _(
        "PostgreSQL data directory initialization state changed: {PREVIOUS} -> {CURRENT}."
    ),
}

MSG_DATABASE_DRIFT_BLOCKING = _(
    "Blocking database configuration drift detected; resolve before starting containers."
)


def format_database_drift_warning(drift: DatabaseDrift) -> str:
    template = _DATABASE_DRIFT_MESSAGES[drift.kind]
    if drift.kind == "first_run":
        return template
    return template.format(PREVIOUS=drift.previous, CURRENT=drift.current)


def collect_database_drift_warnings(config: Config) -> tuple[str, ...]:
    _current, drifts = detect_database_drift_for_config(config)
    if not drifts:
        return ()
    warnings = [format_database_drift_warning(drift) for drift in drifts]
    meaningful = meaningful_database_drifts(drifts)
    if meaningful and has_blocking_database_drift(meaningful):
        warnings.append(MSG_DATABASE_DRIFT_BLOCKING)
    return tuple(warnings)
