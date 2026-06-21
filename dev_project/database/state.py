"""Collect current database fingerprints and persist last_run snapshots."""

from __future__ import annotations

import configparser
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .. import constants
from .paths import ensure_database_dir_gitignore, last_run_path
from .schema import (
    DATABASE_ENGINE_POSTGRES,
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseCurrentState,
    DatabaseLastRun,
    DatabaseOdooConfFingerprint,
)

if TYPE_CHECKING:
    from ..config import Config

_PG_VERSION_FILE = "PG_VERSION"


def _read_pg_major(data_path: str) -> int | None:
    version_file = os.path.join(data_path, _PG_VERSION_FILE)
    if not os.path.isfile(version_file):
        return None
    try:
        with open(version_file, encoding="utf-8") as reader:
            raw = reader.read().strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        return int(raw.split(".", maxsplit=1)[0])
    except ValueError:
        return None


def _data_dir_nonempty(data_path: str) -> bool:
    if not os.path.isdir(data_path):
        return False
    pg_version = os.path.join(data_path, _PG_VERSION_FILE)
    if os.path.isfile(pg_version):
        return True
    try:
        return any(os.scandir(data_path))
    except OSError:
        return False


def read_odoo_conf_db_fingerprint(
    path: str,
    *,
    default_host: str,
    default_port: int,
    default_user: str,
) -> DatabaseOdooConfFingerprint:
    if not os.path.isfile(path):
        return DatabaseOdooConfFingerprint(
            db_host=default_host,
            db_port=default_port,
            db_user=default_user,
        )
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except OSError:
        return DatabaseOdooConfFingerprint(
            db_host=default_host,
            db_port=default_port,
            db_user=default_user,
        )
    if "options" not in parser:
        return DatabaseOdooConfFingerprint(
            db_host=default_host,
            db_port=default_port,
            db_user=default_user,
        )
    options = parser["options"]
    db_host = (options.get("db_host") or "").strip() or default_host
    db_port_raw = (options.get("db_port") or "").strip()
    db_user = (options.get("db_user") or "").strip() or default_user
    try:
        db_port = int(db_port_raw) if db_port_raw else default_port
    except ValueError:
        db_port = default_port
    return DatabaseOdooConfFingerprint(
        db_host=db_host,
        db_port=db_port,
        db_user=db_user,
    )


def collect_database_state(config: Config) -> DatabaseCurrentState:
    data_path = os.path.realpath(config.postgres_data_local_storage)
    service_name = config.user_env.postgres_service_name
    host_port = int(
        config.user_env.postgres_port or constants.POSTGRES_DEFAULT_PORT
    )
    default_user = constants.POSTGRES_ODOO_USER
    odoo_conf = read_odoo_conf_db_fingerprint(
        config.path_odoo_conf,
        default_host=service_name,
        default_port=constants.POSTGRES_ODOO_PORT,
        default_user=default_user,
    )
    return DatabaseCurrentState(
        odpm_scenario=config.policy.scenario,
        engine=DATABASE_ENGINE_POSTGRES,
        compose=DatabaseComposeFingerprint(
            service_name=service_name,
            image_tag=str(config.postgres_version),
            data_path_abs=data_path,
            host_port=host_port,
        ),
        odoo_conf=odoo_conf,
        cluster=DatabaseClusterFingerprint(
            data_dir_nonempty=_data_dir_nonempty(data_path),
            pg_major=_read_pg_major(data_path),
            app_role=default_user,
            app_role_present=None,
        ),
    )


def load_last_run(project_dir: str) -> DatabaseLastRun | None:
    path = last_run_path(project_dir)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as reader:
        data = json.load(reader)
    if not isinstance(data, dict):
        raise ValueError("database last_run.json must be a JSON object")
    return DatabaseLastRun.from_dict(data)


def save_last_run(project_dir: str, snapshot: DatabaseLastRun) -> str:
    ensure_database_dir_gitignore(project_dir)
    return write_last_run_to_path(last_run_path(project_dir), snapshot)


def save_current_database_baseline(
    config: Config,
    *,
    assume_app_role_present: bool = False,
) -> str:
    """Persist current configuration fingerprints as the database baseline."""
    from .status import collect_database_status

    report = collect_database_status(config)
    current = report.current
    if assume_app_role_present:
        current = replace(
            current,
            cluster=replace(current.cluster, app_role_present=True),
        )
    return save_last_run(config.project_dir, current.to_last_run())


def write_last_run_to_path(path: str, snapshot: DatabaseLastRun) -> str:
    if not snapshot.recorded_at:
        snapshot = DatabaseLastRun(
            schema_version=snapshot.schema_version,
            recorded_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            odpm_scenario=snapshot.odpm_scenario,
            engine=snapshot.engine,
            compose=snapshot.compose,
            odoo_conf=snapshot.odoo_conf,
            cluster=snapshot.cluster,
        )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n"
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as writer:
        writer.write(payload)
    os.replace(tmp_path, path)
    return path
