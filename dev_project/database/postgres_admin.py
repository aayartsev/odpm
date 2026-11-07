"""Resolve PostgreSQL admin roles and recover clusters without login roles."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .. import constants
from ..errors import OdpmError
from ..logging import get_module_logger
from ..subprocess_runner import CommandResult
from ..translations import _
from .compose_exec import (
    compose_exec,
    compose_run,
    compose_stop_service,
    compose_up_service_detached,
    postgres_service_name,
)
from .postgres_paths import postgres_pgdata_path

if TYPE_CHECKING:
    from ..host.ports import BootstrapHandle

_logger = get_module_logger(__name__)

_PSQL_ADMIN_WAIT_TIMEOUT_SECONDS = 120
_PSQL_ADMIN_POLL_SECONDS = 2

_MSG_BOOTSTRAP_SINGLE_USER = _(
    "Bootstrapping PostgreSQL application role {ROLE} in single-user mode."
)
_MSG_BOOTSTRAP_FAILED = _(
    "Failed to bootstrap PostgreSQL application role {ROLE} in single-user mode."
)
_MSG_NO_ADMIN_ROLE = _("No PostgreSQL admin role is available for service {SERVICE}.")
_MSG_ADMIN_ROLE_TIMEOUT = _(
    "PostgreSQL admin role did not become available within {SECONDS}s after bootstrap."
)


def admin_role_candidates() -> tuple[str, ...]:
    """Prefer cluster admin role, then application role (legacy SUPERUSER app)."""
    admin_role = constants.POSTGRES_ADMIN_USER
    app_role = constants.POSTGRES_ODOO_USER
    if app_role == admin_role:
        return (app_role,)
    return (admin_role, app_role)


def _exec_users() -> tuple[str | None, ...]:
    return (constants.POSTGRES_CONTAINER_OS_USER, None)


def _run_psql(
    bootstrap: BootstrapHandle,
    pg_role: str,
    database: str,
    *psql_args: str,
    exec_user: str | None = constants.POSTGRES_CONTAINER_OS_USER,
) -> CommandResult:
    return compose_exec(
        bootstrap,
        postgres_service_name(bootstrap),
        "psql",
        "-U",
        pg_role,
        "-d",
        database,
        *psql_args,
        user=exec_user,
    )


def psql_role_connects(bootstrap: BootstrapHandle, pg_role: str, *, database: str = "postgres") -> bool:
    for exec_user in _exec_users():
        result = _run_psql(
            bootstrap,
            pg_role,
            database,
            "-tAc",
            "SELECT 1",
            exec_user=exec_user,
        )
        if result.returncode == 0:
            return True
    return False


def resolve_psql_admin_role(bootstrap: BootstrapHandle) -> str | None:
    for role in admin_role_candidates():
        if psql_role_connects(bootstrap, role):
            return role
    return None


def wait_for_psql_admin_role(
    bootstrap: BootstrapHandle,
    *,
    timeout_seconds: int = _PSQL_ADMIN_WAIT_TIMEOUT_SECONDS,
    poll_seconds: float = _PSQL_ADMIN_POLL_SECONDS,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        admin_role = resolve_psql_admin_role(bootstrap)
        if admin_role is not None:
            return admin_role
        time.sleep(poll_seconds)
    raise OdpmError(
        _MSG_ADMIN_ROLE_TIMEOUT.format(SECONDS=timeout_seconds)
    )


def run_psql_as_admin(
    bootstrap: BootstrapHandle,
    *psql_args: str,
    database: str = "postgres",
) -> CommandResult:
    admin_role = resolve_psql_admin_role(bootstrap)
    if admin_role is None:
        service = postgres_service_name(bootstrap)
        return CommandResult(
            1,
            "",
            _MSG_NO_ADMIN_ROLE.format(SERVICE=service),
        )
    last_result: CommandResult | None = None
    for exec_user in _exec_users():
        last_result = _run_psql(
            bootstrap,
            admin_role,
            database,
            *psql_args,
            exec_user=exec_user,
        )
        if last_result.returncode == 0:
            return last_result
    assert last_result is not None
    return last_result


def bootstrap_app_role_single_user(bootstrap: BootstrapHandle, sql: str) -> None:
    """Create roles via postgres --single when no admin login role is available."""
    service = postgres_service_name(bootstrap)
    role = constants.POSTGRES_ODOO_USER
    _logger.info(_MSG_BOOTSTRAP_SINGLE_USER.format(ROLE=role))

    compose_stop_service(bootstrap, service)
    result = compose_run(
        bootstrap,
        service,
        "--single",
        "-D",
        postgres_pgdata_path(bootstrap.project_settings.postgres_version),
        "postgres",
        user=constants.POSTGRES_CONTAINER_OS_USER,
        entrypoint="postgres",
        input_text=sql if sql.endswith("\n") else f"{sql}\n",
    )
    up_result = compose_up_service_detached(bootstrap, service)
    if up_result.returncode != 0:
        detail = up_result.stderr.strip() or up_result.stdout.strip()
        message = _MSG_BOOTSTRAP_FAILED.format(ROLE=role)
        if detail:
            message = f"{message} {detail}"
        raise OdpmError(message)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        message = _MSG_BOOTSTRAP_FAILED.format(ROLE=role)
        if detail:
            message = f"{message} {detail}"
        raise OdpmError(message)
    _wait_for_postgres_ready(bootstrap)


def _wait_for_postgres_ready(
    bootstrap: BootstrapHandle,
    *,
    timeout_seconds: int = 120,
    poll_seconds: float = 2,
) -> None:
    from .probe import probe_postgres_ready  # noqa: PLC0415  # cycle

    service = postgres_service_name(bootstrap)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if probe_postgres_ready(bootstrap) is True:
            return
        time.sleep(poll_seconds)
    raise OdpmError(
        _(
            "PostgreSQL service {SERVICE} did not become ready within {SECONDS}s "
            "after single-user bootstrap."
        ).format(SECONDS=timeout_seconds, SERVICE=service)
    )
