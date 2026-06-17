"""Database configuration state and last-run snapshots for odpm projects."""

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
from .state import collect_database_state, load_last_run, read_odoo_conf_db_fingerprint, save_last_run
from .drift import (
    DatabaseDrift,
    DatabaseDriftKind,
    DatabaseDriftSeverity,
    database_drift_kinds,
    detect_database_drift,
    has_blocking_database_drift,
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
    "collect_database_state",
    "database_dir_path",
    "database_drift_kinds",
    "detect_database_drift",
    "ensure_database_dir_gitignore",
    "has_blocking_database_drift",
    "last_run_missing",
    "last_run_path",
    "load_last_run",
    "read_odoo_conf_db_fingerprint",
    "save_last_run",
)
