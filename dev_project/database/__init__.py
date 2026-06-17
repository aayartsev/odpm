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

__all__ = (
    "DATABASE_ENGINE_POSTGRES",
    "DATABASE_LAST_RUN_SCHEMA_VERSION",
    "DatabaseClusterFingerprint",
    "DatabaseComposeFingerprint",
    "DatabaseCurrentState",
    "DatabaseLastRun",
    "DatabaseOdooConfFingerprint",
    "collect_database_state",
    "database_dir_path",
    "ensure_database_dir_gitignore",
    "last_run_missing",
    "last_run_path",
    "load_last_run",
    "read_odoo_conf_db_fingerprint",
    "save_last_run",
)
