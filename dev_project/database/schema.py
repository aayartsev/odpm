"""Database last-run snapshot schema (v1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

DATABASE_LAST_RUN_SCHEMA_VERSION = 1
DATABASE_ENGINE_POSTGRES: Literal["postgres"] = "postgres"


@dataclass(frozen=True)
class DatabaseComposeFingerprint:
    service_name: str
    image_tag: str
    data_path_abs: str
    host_port: int
    compose_project_name: str | None = None
    odoo_service_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "service_name": self.service_name,
            "image_tag": self.image_tag,
            "data_path_abs": self.data_path_abs,
            "host_port": self.host_port,
        }
        if self.compose_project_name is not None:
            payload["compose_project_name"] = self.compose_project_name
        if self.odoo_service_name is not None:
            payload["odoo_service_name"] = self.odoo_service_name
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatabaseComposeFingerprint:
        compose_project_name = data.get("compose_project_name")
        odoo_service_name = data.get("odoo_service_name")
        return cls(
            service_name=str(data["service_name"]),
            image_tag=str(data["image_tag"]),
            data_path_abs=str(data["data_path_abs"]),
            host_port=int(data["host_port"]),
            compose_project_name=(
                str(compose_project_name)
                if compose_project_name is not None
                else None
            ),
            odoo_service_name=(
                str(odoo_service_name) if odoo_service_name is not None else None
            ),
        )


@dataclass(frozen=True)
class DatabaseOdooConfFingerprint:
    db_host: str
    db_port: int
    db_user: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_user": self.db_user,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatabaseOdooConfFingerprint:
        return cls(
            db_host=str(data["db_host"]),
            db_port=int(data["db_port"]),
            db_user=str(data["db_user"]),
        )


@dataclass(frozen=True)
class DatabaseClusterFingerprint:
    data_dir_nonempty: bool
    pg_major: int | None
    app_role: str
    app_role_present: bool | None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "data_dir_nonempty": self.data_dir_nonempty,
            "app_role": self.app_role,
        }
        if self.pg_major is not None:
            payload["pg_major"] = self.pg_major
        if self.app_role_present is not None:
            payload["app_role_present"] = self.app_role_present
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatabaseClusterFingerprint:
        pg_major_raw = data.get("pg_major")
        role_present_raw = data.get("app_role_present")
        return cls(
            data_dir_nonempty=bool(data.get("data_dir_nonempty", False)),
            pg_major=int(pg_major_raw) if pg_major_raw is not None else None,
            app_role=str(data.get("app_role", "")),
            app_role_present=(
                bool(role_present_raw) if role_present_raw is not None else None
            ),
        )


@dataclass(frozen=True)
class DatabaseCurrentState:
    odpm_scenario: str
    engine: Literal["postgres"]
    compose: DatabaseComposeFingerprint
    odoo_conf: DatabaseOdooConfFingerprint
    cluster: DatabaseClusterFingerprint

    def to_last_run(self, *, recorded_at: str | None = None) -> DatabaseLastRun:
        timestamp = recorded_at or datetime.now(timezone.utc).replace(
            microsecond=0
        ).isoformat()
        return DatabaseLastRun(
            schema_version=DATABASE_LAST_RUN_SCHEMA_VERSION,
            recorded_at=timestamp,
            odpm_scenario=self.odpm_scenario,
            engine=self.engine,
            compose=self.compose,
            odoo_conf=self.odoo_conf,
            cluster=self.cluster,
        )


@dataclass(frozen=True)
class DatabaseLastRun:
    schema_version: int
    recorded_at: str
    odpm_scenario: str
    engine: Literal["postgres"]
    compose: DatabaseComposeFingerprint
    odoo_conf: DatabaseOdooConfFingerprint
    cluster: DatabaseClusterFingerprint

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "recorded_at": self.recorded_at,
            "odpm_scenario": self.odpm_scenario,
            "engine": self.engine,
            "compose": self.compose.to_dict(),
            "odoo_conf": self.odoo_conf.to_dict(),
            "cluster": self.cluster.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatabaseLastRun:
        version = int(data.get("schema_version", 0))
        if version != DATABASE_LAST_RUN_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported database last_run schema_version: {version}"
            )
        compose_raw = data.get("compose")
        odoo_conf_raw = data.get("odoo_conf")
        cluster_raw = data.get("cluster")
        if not isinstance(compose_raw, dict):
            raise ValueError("compose must be an object")
        if not isinstance(odoo_conf_raw, dict):
            raise ValueError("odoo_conf must be an object")
        if not isinstance(cluster_raw, dict):
            raise ValueError("cluster must be an object")
        engine = str(data.get("engine", ""))
        if engine != DATABASE_ENGINE_POSTGRES:
            raise ValueError(f"unsupported database engine: {engine!r}")
        return cls(
            schema_version=version,
            recorded_at=str(data.get("recorded_at", "")),
            odpm_scenario=str(data.get("odpm_scenario", "")),
            engine=DATABASE_ENGINE_POSTGRES,
            compose=DatabaseComposeFingerprint.from_dict(compose_raw),
            odoo_conf=DatabaseOdooConfFingerprint.from_dict(odoo_conf_raw),
            cluster=DatabaseClusterFingerprint.from_dict(cluster_raw),
        )
