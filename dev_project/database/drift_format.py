"""Human-readable database drift messages (shared by host CLI and plan)."""

from __future__ import annotations

from .drift import DatabaseDrift
from ..translations import _

_DATABASE_DRIFT_MESSAGES = {
    "first_run": _(
        "No database last_run snapshot yet; baseline will be adopted automatically on startup."
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
    "app_role_missing": _(
        "PostgreSQL application role {CURRENT} is missing in the running cluster."
    ),
}


def format_database_drift_warning(drift: DatabaseDrift) -> str:
    template = _DATABASE_DRIFT_MESSAGES[drift.kind]
    if drift.kind == "first_run":
        return template
    if drift.kind == "app_role_missing":
        return template.format(CURRENT=drift.current)
    return template.format(PREVIOUS=drift.previous, CURRENT=drift.current)
