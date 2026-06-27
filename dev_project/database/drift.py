"""Detect drift between current database fingerprints and last_run snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .schema import DatabaseCurrentState, DatabaseLastRun

DatabaseDriftKind = Literal[
    "first_run",
    "service_name",
    "compose_project_name",
    "db_host_mismatch",
    "host_port",
    "data_path",
    "postgres_major",
    "odpm_scenario",
    "data_dir_empty_changed",
    "app_role_missing",
]

DatabaseDriftSeverity = Literal["info", "low", "medium", "high"]

_DRIFT_SEVERITY: dict[DatabaseDriftKind, DatabaseDriftSeverity] = {
    "first_run": "info",
    "service_name": "low",
    "compose_project_name": "low",
    "db_host_mismatch": "low",
    "host_port": "low",
    "data_path": "high",
    "postgres_major": "high",
    "odpm_scenario": "medium",
    "data_dir_empty_changed": "medium",
    "app_role_missing": "high",
}


@dataclass(frozen=True)
class DatabaseDrift:
    kind: DatabaseDriftKind
    severity: DatabaseDriftSeverity
    previous: str
    current: str

    @property
    def reason_id(self) -> str:
        return f"database.drift.{self.kind}"


def _drift(
    kind: DatabaseDriftKind,
    *,
    previous: str,
    current: str,
) -> DatabaseDrift:
    return DatabaseDrift(
        kind=kind,
        severity=_DRIFT_SEVERITY[kind],
        previous=previous,
        current=current,
    )


def _detect_internal_drifts(current: DatabaseCurrentState) -> list[DatabaseDrift]:
    drifts: list[DatabaseDrift] = []
    expected_host = current.compose.service_name
    actual_host = current.odoo_conf.db_host
    if actual_host != expected_host:
        drifts.append(
            _drift(
                "db_host_mismatch",
                previous=expected_host,
                current=actual_host,
            )
        )
    if current.cluster.app_role_present is False:
        drifts.append(
            _drift(
                "app_role_missing",
                previous="",
                current=current.cluster.app_role,
            )
        )
    return drifts


def _detect_last_run_drifts(
    current: DatabaseCurrentState,
    last_run: DatabaseLastRun,
) -> list[DatabaseDrift]:
    drifts: list[DatabaseDrift] = []
    if current.compose.service_name != last_run.compose.service_name:
        drifts.append(
            _drift(
                "service_name",
                previous=last_run.compose.service_name,
                current=current.compose.service_name,
            )
        )
    previous_project = last_run.compose.compose_project_name or ""
    current_project = current.compose.compose_project_name or ""
    if current_project != previous_project:
        drifts.append(
            _drift(
                "compose_project_name",
                previous=previous_project,
                current=current_project,
            )
        )
    if current.compose.data_path_abs != last_run.compose.data_path_abs:
        drifts.append(
            _drift(
                "data_path",
                previous=last_run.compose.data_path_abs,
                current=current.compose.data_path_abs,
            )
        )
    if current.compose.image_tag != last_run.compose.image_tag:
        drifts.append(
            _drift(
                "postgres_major",
                previous=last_run.compose.image_tag,
                current=current.compose.image_tag,
            )
        )
    if current.compose.host_port != last_run.compose.host_port:
        drifts.append(
            _drift(
                "host_port",
                previous=str(last_run.compose.host_port),
                current=str(current.compose.host_port),
            )
        )
    if current.odpm_scenario != last_run.odpm_scenario:
        drifts.append(
            _drift(
                "odpm_scenario",
                previous=last_run.odpm_scenario,
                current=current.odpm_scenario,
            )
        )
    if current.cluster.data_dir_nonempty != last_run.cluster.data_dir_nonempty:
        drifts.append(
            _drift(
                "data_dir_empty_changed",
                previous=str(last_run.cluster.data_dir_nonempty),
                current=str(current.cluster.data_dir_nonempty),
            )
        )
    return drifts


def detect_database_drift(
    current: DatabaseCurrentState,
    last_run: DatabaseLastRun | None,
) -> tuple[DatabaseDrift, ...]:
    """Return ordered drift records for *current* vs *last_run* (None = first run)."""
    drifts: list[DatabaseDrift] = []
    if last_run is None:
        drifts.append(_drift("first_run", previous="", current=""))
    else:
        drifts.extend(_detect_last_run_drifts(current, last_run))
    drifts.extend(_detect_internal_drifts(current))
    return tuple(drifts)


def has_blocking_database_drift(drifts: tuple[DatabaseDrift, ...]) -> bool:
    return any(drift.severity == "high" for drift in drifts)


def database_drift_kinds(drifts: tuple[DatabaseDrift, ...]) -> frozenset[DatabaseDriftKind]:
    return frozenset(drift.kind for drift in drifts)


def detect_database_drift_for_config(config) -> tuple[DatabaseCurrentState, tuple[DatabaseDrift, ...]]:
    """Collect current DB fingerprints and compare with on-disk last_run snapshot."""
    from .state import collect_database_state, load_last_run

    current = collect_database_state(config)
    last_run = load_last_run(config.project_dir)
    return current, detect_database_drift(current, last_run)


def meaningful_database_drifts(
    drifts: tuple[DatabaseDrift, ...],
) -> tuple[DatabaseDrift, ...]:
    return tuple(drift for drift in drifts if drift.kind != "first_run")


RESOLUTION_DRIFT_KINDS: frozenset[DatabaseDriftKind] = frozenset(
    {
        "data_path",
        "postgres_major",
        "app_role_missing",
        "odpm_scenario",
        "data_dir_empty_changed",
    }
)


def drifts_requiring_resolution(
    drifts: tuple[DatabaseDrift, ...],
) -> tuple[DatabaseDrift, ...]:
    return tuple(
        drift for drift in meaningful_database_drifts(drifts)
        if drift.kind in RESOLUTION_DRIFT_KINDS
    )
