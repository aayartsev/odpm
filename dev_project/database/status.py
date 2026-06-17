"""Collect and format database status for odpm database status."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from ..plan.database_preview import format_database_drift_warning
from .drift import DatabaseDrift, detect_database_drift, meaningful_database_drifts
from .probe import (
    probe_app_role_exists,
    probe_postgres_container_running,
    probe_postgres_ready,
)
from .schema import DatabaseCurrentState, DatabaseLastRun
from .state import collect_database_state, load_last_run

if TYPE_CHECKING:
    from ..config import Config


@dataclass(frozen=True)
class DatabaseStatusReport:
    current: DatabaseCurrentState
    last_run: DatabaseLastRun | None
    drifts: tuple[DatabaseDrift, ...]
    postgres_container_running: bool | None
    postgres_ready: bool | None
    app_role_present: bool | None


def collect_database_status(config: Config) -> DatabaseStatusReport:
    current = collect_database_state(config)
    last_run = load_last_run(config.project_dir)
    container_running = probe_postgres_container_running(config)
    postgres_ready = probe_postgres_ready(config) if container_running else None
    app_role_present = None
    if postgres_ready:
        app_role_present = probe_app_role_exists(
            config, role=current.cluster.app_role
        )
    if app_role_present is not None:
        current = replace(
            current,
            cluster=replace(
                current.cluster,
                app_role_present=app_role_present,
            ),
        )
    drifts = detect_database_drift(current, last_run)
    return DatabaseStatusReport(
        current=current,
        last_run=last_run,
        drifts=drifts,
        postgres_container_running=container_running,
        postgres_ready=postgres_ready,
        app_role_present=app_role_present,
    )


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def format_database_status_table(report: DatabaseStatusReport) -> str:
    from ..translations import _

    lines = [
        _("Database status"),
        "",
        _("Compose service: {SERVICE}").format(
            SERVICE=report.current.compose.service_name
        ),
        _("Data path: {PATH}").format(PATH=report.current.compose.data_path_abs),
        _("Host port: {PORT}").format(PORT=report.current.compose.host_port),
        _("odoo.conf db_host: {HOST}").format(HOST=report.current.odoo_conf.db_host),
        _("PostgreSQL container running: {VALUE}").format(
            VALUE=_format_bool(report.postgres_container_running)
        ),
        _("PostgreSQL ready: {VALUE}").format(VALUE=_format_bool(report.postgres_ready)),
        _("Application role {ROLE} present: {VALUE}").format(
            ROLE=report.current.cluster.app_role,
            VALUE=_format_bool(report.app_role_present),
        ),
        "",
    ]
    meaningful = meaningful_database_drifts(report.drifts)
    if not meaningful:
        if any(drift.kind == "first_run" for drift in report.drifts):
            lines.append(_("first database run (no last_run snapshot yet)"))
        else:
            lines.append(_("database configuration matches last_run snapshot"))
    else:
        lines.append(_("Configuration drift:"))
        for drift in report.drifts:
            if drift.kind == "first_run":
                continue
            lines.append(f"  - {format_database_drift_warning(drift)}")
    return "\n".join(lines)


def database_status_to_dict(report: DatabaseStatusReport) -> dict[str, Any]:
    return {
        "compose": report.current.compose.to_dict(),
        "odoo_conf": report.current.odoo_conf.to_dict(),
        "cluster": report.current.cluster.to_dict(),
        "last_run_present": report.last_run is not None,
        "postgres_container_running": report.postgres_container_running,
        "postgres_ready": report.postgres_ready,
        "app_role_present": report.app_role_present,
        "drifts": [
            {
                "kind": drift.kind,
                "severity": drift.severity,
                "previous": drift.previous,
                "current": drift.current,
            }
            for drift in report.drifts
            if drift.kind != "first_run"
        ],
        "first_run": any(drift.kind == "first_run" for drift in report.drifts),
    }


def format_database_status_json(report: DatabaseStatusReport) -> str:
    return json.dumps(database_status_to_dict(report), indent=2, sort_keys=True) + "\n"
