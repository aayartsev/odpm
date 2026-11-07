"""Live PostgreSQL probes via docker compose exec."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import constants
from .compose_exec import compose_exec, postgres_container_id, postgres_service_name
from .postgres_admin import psql_role_connects, resolve_psql_admin_role, run_psql_as_admin

if TYPE_CHECKING:
    from ..host.ports import BootstrapHandle


def probe_postgres_container_running(bootstrap: BootstrapHandle) -> bool | None:
    """True when the postgres compose service has a running container."""
    return postgres_container_id(bootstrap) is not None


def probe_postgres_ready(bootstrap: BootstrapHandle) -> bool | None:
    """True when pg_isready succeeds inside the postgres container."""
    if not probe_postgres_container_running(bootstrap):
        return None
    result = compose_exec(
        bootstrap,
        postgres_service_name(bootstrap),
        "pg_isready",
        "-q",
        user=constants.POSTGRES_CONTAINER_OS_USER,
    )
    return result.returncode == 0


def probe_app_role_exists(bootstrap: BootstrapHandle, *, role: str) -> bool | None:
    """True when *role* exists in pg_roles; None when postgres is not probeable."""
    if probe_postgres_ready(bootstrap) is not True:
        return None
    if psql_role_connects(bootstrap, role):
        return True
    if resolve_psql_admin_role(bootstrap) is None:
        return False
    sql = (
        "SELECT 1 FROM pg_catalog.pg_roles "
        f"WHERE rolname = '{role.replace(chr(39), chr(39) * 2)}'"
    )
    result = run_psql_as_admin(bootstrap, "-tAc", sql)
    if result.returncode != 0:
        return None
    return result.stdout.strip() == "1"
