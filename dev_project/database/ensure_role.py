"""Ensure the Odoo application role exists in a running PostgreSQL cluster."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .. import constants
from ..errors import OdpmError
from ..translations import _
from .compose_exec import postgres_service_name
from .postgres_admin import (
    bootstrap_app_role_single_user,
    psql_role_connects,
    resolve_psql_admin_role,
    run_psql_as_admin,
    wait_for_psql_admin_role,
)
from .probe import probe_app_role_exists, probe_postgres_ready

if TYPE_CHECKING:
    from ..config import Config

EnsureRoleOutcome = Literal["created", "updated"]


@dataclass(frozen=True)
class EnsureRoleResult:
    outcome: EnsureRoleOutcome
    role: str


def build_ensure_role_sql(role: str, password: str) -> str:
    """Return idempotent SQL that creates or updates the application role."""
    safe_role = role.replace("'", "''")
    safe_password = password.replace("'", "''")
    return (
        "DO $$\n"
        "BEGIN\n"
        "  IF NOT EXISTS ("
        "SELECT FROM pg_catalog.pg_roles WHERE rolname = "
        f"'{safe_role}'"
        ") THEN\n"
        f"    CREATE ROLE {safe_role} LOGIN SUPERUSER CREATEDB PASSWORD '{safe_password}';\n"
        "  ELSE\n"
        f"    ALTER ROLE {safe_role} WITH LOGIN SUPERUSER CREATEDB PASSWORD '{safe_password}';\n"
        "  END IF;\n"
        "END\n"
        "$$;"
    )


def build_single_user_bootstrap_sql(role: str, password: str) -> str:
    """Plain SQL for postgres --single (PL/pgSQL DO blocks are unavailable there)."""
    safe_role = role.replace("'", "''")
    safe_password = password.replace("'", "''")
    return (
        f"CREATE ROLE {safe_role} LOGIN SUPERUSER CREATEDB PASSWORD '{safe_password}';\n"
    )


def ensure_app_role(config: Config) -> EnsureRoleResult:
    """Create or update the configured application role in PostgreSQL."""
    role = constants.POSTGRES_ODOO_USER
    password = constants.POSTGRES_ODOO_PASS
    ready = probe_postgres_ready(config)
    if ready is None:
        raise OdpmError(
            _(
                "PostgreSQL container {SERVICE} is not running; start it before ensuring the role."
            ).format(SERVICE=postgres_service_name(config))
        )
    if ready is False:
        raise OdpmError(
            _(
                "PostgreSQL in {SERVICE} is not ready yet; wait for startup before ensuring the role."
            ).format(SERVICE=postgres_service_name(config))
        )
    existed_before = probe_app_role_exists(config, role=role) is True
    sql = build_ensure_role_sql(role, password)
    if resolve_psql_admin_role(config) is None:
        bootstrap_app_role_single_user(
            config,
            build_single_user_bootstrap_sql(role, password),
        )
        wait_for_psql_admin_role(config)
    if psql_role_connects(config, role):
        if not existed_before:
            return EnsureRoleResult(outcome="created", role=role)
        return EnsureRoleResult(outcome="updated", role=role)
    result = run_psql_as_admin(
        config,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        message = _("Failed to ensure PostgreSQL role {ROLE}.").format(ROLE=role)
        if detail:
            message = f"{message} {detail}"
        raise OdpmError(message)
    if not existed_before:
        return EnsureRoleResult(outcome="created", role=role)
    return EnsureRoleResult(outcome="updated", role=role)
