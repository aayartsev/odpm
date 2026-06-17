"""Live PostgreSQL probes via docker compose exec."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .compose_exec import compose_exec, postgres_container_id, postgres_service_name

if TYPE_CHECKING:
    from ..config import Config


def probe_postgres_container_running(config: Config) -> bool | None:
    """True when the postgres compose service has a running container."""
    return postgres_container_id(config) is not None


def probe_postgres_ready(config: Config) -> bool | None:
    """True when pg_isready succeeds inside the postgres container."""
    if not probe_postgres_container_running(config):
        return None
    result = compose_exec(
        config,
        postgres_service_name(config),
        "pg_isready",
        "-q",
        user="postgres",
    )
    return result.returncode == 0


def probe_app_role_exists(config: Config, *, role: str) -> bool | None:
    """True when *role* exists in pg_roles; None when postgres is not probeable."""
    if probe_postgres_ready(config) is not True:
        return None
    sql = (
        "SELECT 1 FROM pg_catalog.pg_roles "
        f"WHERE rolname = '{role.replace(chr(39), chr(39) * 2)}'"
    )
    result = compose_exec(
        config,
        postgres_service_name(config),
        "psql",
        "-U",
        "postgres",
        "-d",
        "postgres",
        "-tAc",
        sql,
        user="postgres",
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() == "1"
