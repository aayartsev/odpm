"""Database configuration state and last-run snapshots for odpm projects.

Leaf types live in :mod:`dev_project.database.schema` and path helpers in
:mod:`dev_project.database.paths`. Heavier modules (state, drift, probe, …)
load lazily so ``container_config`` can import schema/state without a cycle
through this package ``__init__``.
"""

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
    "collect_database_state": (".state", "collect_database_state"),
    "load_last_run": (".state", "load_last_run"),
    "read_odoo_conf_db_fingerprint": (".state", "read_odoo_conf_db_fingerprint"),
    "save_last_run": (".state", "save_last_run"),
    "EnsureRoleResult": (".ensure_role", "EnsureRoleResult"),
    "build_ensure_role_sql": (".ensure_role", "build_ensure_role_sql"),
    "ensure_app_role": (".ensure_role", "ensure_app_role"),
    "probe_app_role_exists": (".probe", "probe_app_role_exists"),
    "probe_postgres_container_running": (".probe", "probe_postgres_container_running"),
    "probe_postgres_ready": (".probe", "probe_postgres_ready"),
    "RESOLUTION_DRIFT_KINDS": (".drift", "RESOLUTION_DRIFT_KINDS"),
    "DatabaseDrift": (".drift", "DatabaseDrift"),
    "DatabaseDriftKind": (".drift", "DatabaseDriftKind"),
    "DatabaseDriftSeverity": (".drift", "DatabaseDriftSeverity"),
    "database_drift_kinds": (".drift", "database_drift_kinds"),
    "detect_database_drift": (".drift", "detect_database_drift"),
    "detect_database_drift_for_config": (".drift", "detect_database_drift_for_config"),
    "drifts_requiring_resolution": (".drift", "drifts_requiring_resolution"),
    "has_blocking_database_drift": (".drift", "has_blocking_database_drift"),
    "meaningful_database_drifts": (".drift", "meaningful_database_drifts"),
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
    if target is not None:
        module_name, attr_name = target
        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)
    try:
        return importlib.import_module(f".{name}", __name__)
    except ModuleNotFoundError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()) | set(_LAZY_EXPORTS))
