"""Database fingerprint payload embedded in container runtime config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import Config
    from ..database.schema import DatabaseCurrentState, DatabaseLastRun


@dataclass(frozen=True)
class DatabaseContainerContext:
    service_name: str
    image_tag: str
    data_path_abs: str
    host_port: int
    data_dir_nonempty: bool
    pg_major: int | None
    app_role: str
    db_host: str
    db_port: int
    db_user: str

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "service_name": self.service_name,
            "image_tag": self.image_tag,
            "data_path_abs": self.data_path_abs,
            "host_port": self.host_port,
            "data_dir_nonempty": self.data_dir_nonempty,
            "app_role": self.app_role,
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_user": self.db_user,
        }
        if self.pg_major is not None:
            payload["pg_major"] = self.pg_major
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatabaseContainerContext:
        pg_major_raw = data.get("pg_major")
        return cls(
            service_name=str(data["service_name"]),
            image_tag=str(data["image_tag"]),
            data_path_abs=str(data["data_path_abs"]),
            host_port=int(data["host_port"]),
            data_dir_nonempty=bool(data.get("data_dir_nonempty", False)),
            pg_major=int(pg_major_raw) if pg_major_raw is not None else None,
            app_role=str(data.get("app_role", "")),
            db_host=str(data["db_host"]),
            db_port=int(data["db_port"]),
            db_user=str(data["db_user"]),
        )

    @classmethod
    def from_host_config(cls, config: Config) -> DatabaseContainerContext:
        from ..database.state import collect_database_state

        state = collect_database_state(config)
        return cls(
            service_name=state.compose.service_name,
            image_tag=state.compose.image_tag,
            data_path_abs=state.compose.data_path_abs,
            host_port=state.compose.host_port,
            data_dir_nonempty=state.cluster.data_dir_nonempty,
            pg_major=state.cluster.pg_major,
            app_role=state.cluster.app_role,
            db_host=state.odoo_conf.db_host,
            db_port=state.odoo_conf.db_port,
            db_user=state.odoo_conf.db_user,
        )

    def to_current_state(
        self, odpm_scenario: str, *, app_role_present: bool
    ) -> DatabaseCurrentState:
        from ..database.schema import (
            DATABASE_ENGINE_POSTGRES,
            DatabaseClusterFingerprint,
            DatabaseComposeFingerprint,
            DatabaseCurrentState,
            DatabaseOdooConfFingerprint,
        )

        return DatabaseCurrentState(
            odpm_scenario=odpm_scenario,
            engine=DATABASE_ENGINE_POSTGRES,
            compose=DatabaseComposeFingerprint(
                service_name=self.service_name,
                image_tag=self.image_tag,
                data_path_abs=self.data_path_abs,
                host_port=self.host_port,
            ),
            odoo_conf=DatabaseOdooConfFingerprint(
                db_host=self.db_host,
                db_port=self.db_port,
                db_user=self.db_user,
            ),
            cluster=DatabaseClusterFingerprint(
                data_dir_nonempty=self.data_dir_nonempty,
                pg_major=self.pg_major,
                app_role=self.app_role,
                app_role_present=app_role_present,
            ),
        )

    def to_last_run(
        self, odpm_scenario: str, *, app_role_present: bool
    ) -> DatabaseLastRun:
        return self.to_current_state(
            odpm_scenario, app_role_present=app_role_present
        ).to_last_run()
