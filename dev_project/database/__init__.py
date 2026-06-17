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
from .commands import run_database_command
from .ensure_role import EnsureRoleResult, build_ensure_role_sql, ensure_app_role
from .probe import (
    probe_app_role_exists,
    probe_postgres_container_running,
    probe_postgres_ready,
)
from .status import (
    DatabaseStatusReport,
    collect_database_status,
    database_status_to_dict,
    format_database_status_json,
    format_database_status_table,
)
from .drift import (
    DatabaseDrift,
    DatabaseDriftKind,
    DatabaseDriftSeverity,
    database_drift_kinds,
    detect_database_drift,
    detect_database_drift_for_config,
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
    "collect_database_state",
    "collect_database_status",
    "database_dir_path",
    "database_drift_kinds",
    "database_status_to_dict",
    "detect_database_drift",
    "detect_database_drift_for_config",
    "ensure_app_role",
    "ensure_database_dir_gitignore",
    "format_database_status_json",
    "format_database_status_table",
    "has_blocking_database_drift",
    "last_run_missing",
    "last_run_path",
    "load_last_run",
    "meaningful_database_drifts",
    "probe_app_role_exists",
    "probe_postgres_container_running",
    "probe_postgres_ready",
    "read_odoo_conf_db_fingerprint",
    "run_database_command",
    "save_last_run",
    "build_ensure_role_sql",
)
