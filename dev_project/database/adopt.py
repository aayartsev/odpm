"""Adopt legacy projects without last_run.json as the database baseline."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import TYPE_CHECKING

from .. import constants
from ..errors import OdpmError
from ..logging import get_module_logger
from ..translations import _
from .compose_exec import (
    compose_up_service_detached,
    postgres_service_name,
)
from .ensure_role import ensure_app_role
from .paths import last_run_missing
from .probe import probe_app_role_exists, probe_postgres_ready
from .state import collect_database_state, save_last_run

if TYPE_CHECKING:
    from ..config import Config

_logger = get_module_logger(__name__)

_POSTGRES_READY_TIMEOUT_SECONDS = 120
_POSTGRES_READY_POLL_SECONDS = 2

_MSG_ADOPTING = _(
    "Adopting current database configuration as baseline (no last_run snapshot yet)."
)
_MSG_STARTING_POSTGRES = _("Starting PostgreSQL service {SERVICE} for baseline adoption.")
_MSG_POSTGRES_TIMEOUT = _(
    "PostgreSQL service {SERVICE} did not become ready within {SECONDS}s during baseline adoption."
)
_MSG_ENSURED_ROLE = _(
    "Ensured PostgreSQL application role {ROLE} during baseline adoption."
)
_MSG_BASELINE_RECORDED = _("Recorded database baseline snapshot at {PATH}.")
_MSG_COMPOSE_UP_FAILED = _(
    "Failed to start PostgreSQL service {SERVICE} for baseline adoption."
)


def needs_database_adoption(config: Config) -> bool:
    """True when the project has no last_run snapshot and uses host DB state."""
    if not config.policy.mount_runtime_config_from_host():
        return False
    return last_run_missing(config.project_dir)


def start_postgres_detached(config: Config) -> None:
    service = postgres_service_name(config)
    result = compose_up_service_detached(config, service)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        message = _MSG_COMPOSE_UP_FAILED.format(SERVICE=service)
        if detail:
            message = f"{message} {detail}"
        raise OdpmError(message)


def wait_for_postgres_ready(
    config: Config,
    *,
    timeout_seconds: int = _POSTGRES_READY_TIMEOUT_SECONDS,
    poll_seconds: float = _POSTGRES_READY_POLL_SECONDS,
) -> None:
    service = postgres_service_name(config)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if probe_postgres_ready(config) is True:
            return
        time.sleep(poll_seconds)
    raise OdpmError(
        _MSG_POSTGRES_TIMEOUT.format(SECONDS=timeout_seconds, SERVICE=service)
    )


def build_adoption_last_run(config: Config):
    state = collect_database_state(config)
    state_with_role = replace(
        state,
        cluster=replace(state.cluster, app_role_present=True),
    )
    return state_with_role.to_last_run()


def adopt_database_baseline(config: Config) -> str | None:
    """Bootstrap database state for legacy projects; return last_run path or None."""
    if not needs_database_adoption(config):
        return None

    _logger.info(_MSG_ADOPTING)
    service = postgres_service_name(config)
    if probe_postgres_ready(config) is not True:
        _logger.info(_MSG_STARTING_POSTGRES.format(SERVICE=service))
        start_postgres_detached(config)
        wait_for_postgres_ready(config)

    role = constants.POSTGRES_ODOO_USER
    existed_before = probe_app_role_exists(config, role=role) is True
    ensure_app_role(config)
    if not existed_before:
        _logger.info(_MSG_ENSURED_ROLE.format(ROLE=role))

    path = save_last_run(config.project_dir, build_adoption_last_run(config))
    _logger.info(_MSG_BASELINE_RECORDED.format(PATH=path))
    return path
