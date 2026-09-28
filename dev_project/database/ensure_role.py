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
    resolve_psql_admin_role,
    run_psql_as_admin,
    wait_for_psql_admin_role,
)
from .probe import probe_app_role_exists, probe_postgres_ready

if TYPE_CHECKING:
    from ..config import Config

EnsureRoleOutcome = Literal["created", "updated"]

_EXTENSIONS = ("unaccent", "pg_trgm")


@dataclass(frozen=True)
class EnsureRoleResult:
    outcome: EnsureRoleOutcome
    role: str


def _sql_ident(name: str) -> str:
    """Quote a PostgreSQL identifier when needed."""
    if name.isidentifier() and name.isascii() and not name.startswith("_"):
        # Unquoted form matches historical test expectations for simple roles.
        return name
    return '"' + name.replace('"', '""') + '"'


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def build_ensure_cluster_roles_sql(
    admin_role: str,
    app_role: str,
    password: str,
) -> str:
    """Idempotent SQL: ensure admin SUPERUSER, then app NOSUPERUSER CREATEDB."""
    admin = _sql_ident(admin_role)
    app = _sql_ident(app_role)
    safe_password = _sql_literal(password)
    safe_admin = _sql_literal(admin_role)
    safe_app = _sql_literal(app_role)
    if admin_role == app_role:
        return (
            "DO $$\n"
            "BEGIN\n"
            "  IF NOT EXISTS ("
            "SELECT FROM pg_catalog.pg_roles WHERE rolname = "
            f"'{safe_admin}'"
            ") THEN\n"
            f"    CREATE ROLE {admin} LOGIN SUPERUSER CREATEDB "
            f"PASSWORD '{safe_password}';\n"
            "  ELSE\n"
            f"    ALTER ROLE {admin} WITH LOGIN SUPERUSER CREATEDB "
            f"PASSWORD '{safe_password}';\n"
            "  END IF;\n"
            "END\n"
            "$$;"
        )
    return (
        "DO $$\n"
        "BEGIN\n"
        "  IF NOT EXISTS ("
        "SELECT FROM pg_catalog.pg_roles WHERE rolname = "
        f"'{safe_admin}'"
        ") THEN\n"
        f"    CREATE ROLE {admin} LOGIN SUPERUSER PASSWORD '{safe_password}';\n"
        "  ELSE\n"
        f"    ALTER ROLE {admin} WITH LOGIN SUPERUSER PASSWORD '{safe_password}';\n"
        "  END IF;\n"
        "  IF NOT EXISTS ("
        "SELECT FROM pg_catalog.pg_roles WHERE rolname = "
        f"'{safe_app}'"
        ") THEN\n"
        f"    CREATE ROLE {app} LOGIN NOSUPERUSER CREATEDB PASSWORD '{safe_password}';\n"
        "  ELSE\n"
        f"    ALTER ROLE {app} WITH LOGIN NOSUPERUSER CREATEDB PASSWORD '{safe_password}';\n"
        "  END IF;\n"
        "END\n"
        "$$;"
    )


def build_ensure_role_sql(role: str, password: str) -> str:
    """Compatibility wrapper: ensure cluster admin + application role."""
    return build_ensure_cluster_roles_sql(
        constants.POSTGRES_ADMIN_USER,
        role,
        password,
    )


def build_single_user_bootstrap_sql(
    app_role: str | None = None,
    password: str | None = None,
    *,
    admin_role: str | None = None,
) -> str:
    """Plain SQL for postgres --single (no PL/pgSQL DO blocks).

    Creates both the cluster admin (SUPERUSER) and application
    (NOSUPERUSER CREATEDB) roles. Callers should only invoke this when no
    login admin is available (fresh/broken cluster).
    """
    admin_name = admin_role or constants.POSTGRES_ADMIN_USER
    app_name = app_role or constants.POSTGRES_ODOO_USER
    admin = _sql_ident(admin_name)
    app = _sql_ident(app_name)
    safe_password = _sql_literal(password or constants.POSTGRES_ODOO_PASS)
    if admin_name == app_name:
        return (
            f"CREATE ROLE {admin} LOGIN SUPERUSER CREATEDB "
            f"PASSWORD '{safe_password}';\n"
        )
    return (
        f"CREATE ROLE {admin} LOGIN SUPERUSER PASSWORD '{safe_password}';\n"
        f"CREATE ROLE {app} LOGIN NOSUPERUSER CREATEDB PASSWORD '{safe_password}';\n"
    )


def build_ensure_extensions_sql() -> str:
    """CREATE EXTENSION IF NOT EXISTS for Odoo-common extensions."""
    return "".join(
        f'CREATE EXTENSION IF NOT EXISTS "{name}";\n' for name in _EXTENSIONS
    )


def ensure_app_role(config: Config) -> EnsureRoleResult:
    """Create or update cluster admin + application role; install template1 extensions."""
    admin_role = constants.POSTGRES_ADMIN_USER
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
    roles_sql = build_ensure_cluster_roles_sql(admin_role, role, password)
    if resolve_psql_admin_role(config) is None:
        bootstrap_app_role_single_user(
            config,
            build_single_user_bootstrap_sql(role, password, admin_role=admin_role),
        )
        wait_for_psql_admin_role(config)
    result = run_psql_as_admin(
        config,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        roles_sql,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        message = _("Failed to ensure PostgreSQL role {ROLE}.").format(ROLE=role)
        if detail:
            message = f"{message} {detail}"
        raise OdpmError(message)
    ext_result = run_psql_as_admin(
        config,
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        build_ensure_extensions_sql(),
        database="template1",
    )
    if ext_result.returncode != 0:
        detail = ext_result.stderr.strip() or ext_result.stdout.strip()
        message = _(
            "Failed to ensure PostgreSQL extensions on template1."
        )
        if detail:
            message = f"{message} {detail}"
        raise OdpmError(message)
    if not existed_before:
        return EnsureRoleResult(outcome="created", role=role)
    return EnsureRoleResult(outcome="updated", role=role)
