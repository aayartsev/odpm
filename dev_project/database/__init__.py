"""Database configuration state and last-run snapshots for odpm projects."""

from __future__ import annotations

import importlib
from typing import Any

from .paths import (
    database_dir_path,
    ensure_database_dir_gitignore,
    last_run_missing,
    last_run_path,
)
from .schema import (
    DATABASE_ENGINE_POSTGRES,
    DATABASE_LAST_RUN_SCHEMA_VERSION,
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseCurrentState,
    DatabaseLastRun,
    DatabaseOdooConfFingerprint,
)
from .state import (
    collect_database_state,
    load_last_run,
    read_odoo_conf_db_fingerprint,
    save_last_run,
)
from .ensure_role import EnsureRoleResult, build_ensure_role_sql, ensure_app_role
from .probe import (
    probe_app_role_exists,
    probe_postgres_container_running,
    probe_postgres_ready,
)
from .drift import (
    RESOLUTION_DRIFT_KINDS,
    DatabaseDrift,
    DatabaseDriftKind,
    DatabaseDriftSeverity,
    database_drift_kinds,
    detect_database_drift,
    detect_database_drift_for_config,
    drifts_requiring_resolution,
    has_blocking_database_drift,
    meaningful_database_drifts,
)

__all__ = (
    "DATABASE_ENGINE_POSTGRES",
    "DATABASE_LAST_RUN_SCHEMA_VERSION",
    "DatabaseClusterFingerprint",
    "DatabaseComposeFingerprint",
    "DatabaseCurrentState",
    "DatabaseDrift",
    "DatabaseDriftKind",
    "DatabaseDriftSeverity",
    "DatabaseLastRun",
    "DatabaseOdooConfFingerprint",
    "DatabaseStatusReport",
    "EnsureRoleResult",
    "RESOLUTION_DRIFT_KINDS",
    "accepted_drift_kinds",
    "adopt_database_baseline",
    "collect_database_state",
    "collect_database_status",
    "database_dir_path",
    "database_drift_kinds",
    "database_status_to_dict",
    "detect_database_drift",
    "detect_database_drift_for_config",
    "drifts_requiring_resolution",
    "ensure_no_blocking_database_drift",
    "ensure_database_dir_gitignore",
    "format_database_status_json",
    "format_database_status_table",
    "has_blocking_database_drift",
    "last_run_missing",
    "last_run_path",
    "load_last_run",
    "meaningful_database_drifts",
    "needs_database_adoption",
    "probe_app_role_exists",
    "probe_postgres_container_running",
    "pending_resolution_drifts",
    "resolve_database_drifts",
    "probe_postgres_ready",
    "ensure_app_role",
    "read_odoo_conf_db_fingerprint",
    "run_database_command",
    "save_last_run",
    "build_ensure_role_sql",
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "run_database_command": (".commands", "run_database_command"),
    "DatabaseStatusReport": (".status", "DatabaseStatusReport"),
    "collect_database_status": (".status", "collect_database_status"),
    "database_status_to_dict": (".status", "database_status_to_dict"),
    "format_database_status_json": (".status", "format_database_status_json"),
    "format_database_status_table": (".status", "format_database_status_table"),
    "accepted_drift_kinds": (".resolve", "accepted_drift_kinds"),
    "ensure_no_blocking_database_drift": (".resolve", "ensure_no_blocking_database_drift"),
    "pending_resolution_drifts": (".resolve", "pending_resolution_drifts"),
    "resolve_database_drifts": (".resolve", "resolve_database_drifts"),
    "adopt_database_baseline": (".adopt", "adopt_database_baseline"),
    "needs_database_adoption": (".adopt", "needs_database_adoption"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = importlib.import_module(module_name, __name__)
    return getattr(module, attr_name)
