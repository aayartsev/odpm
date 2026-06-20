"""Interactive and non-interactive resolution of database configuration drift."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from ..errors import PipelineError
from ..interactive import prompt_input, stdin_is_interactive
from ..logging import get_module_logger
from ..translations import _
from .drift_format import format_database_drift_warning
from .drift import (
    DatabaseDrift,
    drifts_requiring_resolution,
)
from .ensure_role import ensure_app_role
from .state import save_current_database_baseline
from .status import collect_database_status

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs
    from ..prepare.types import PrepareContext

_logger = get_module_logger(__name__)

_MSG_ACCEPTED = _("Accepted database drift: {KIND}")
_MSG_ABORTED = _("Database drift resolution aborted.")
_MSG_NON_INTERACTIVE = _(
    "Database configuration drift requires confirmation in non-interactive mode. "
    "Drift kinds: {KINDS}. Use --accept-database-drift=KIND for each accepted drift."
)
_MSG_STILL_BLOCKING = _(
    "Blocking database configuration drift remains after resolution: {KINDS}"
)
_MSG_BASELINE_UPDATED = _("Updated database baseline snapshot at {PATH}.")
_MSG_DATA_PATH_PROMPT = _(
    "PostgreSQL data directory changed:\n"
    "  previous: {PREVIOUS}\n"
    "  current: {CURRENT}\n"
    "Choose: (a) abort  (b) accept new data path  (c) show wipe instructions\n"
)
_MSG_POSTGRES_MAJOR_PROMPT = _(
    "PostgreSQL image version changed:\n"
    "  previous: {PREVIOUS}\n"
    "  current: {CURRENT}\n"
    "Choose: (a) abort  (b) accept and continue  (c) show wipe instructions\n"
)
_MSG_APP_ROLE_PROMPT = _(
    "PostgreSQL application role {ROLE} is missing in the running cluster.\n"
    "Choose: (a) abort  (b) create role now\n"
)
_MSG_SCENARIO_PROMPT = _(
    "ODPM scenario changed: {PREVIOUS} -> {CURRENT}.\n"
    "Choose: (a) abort  (c) continue\n"
)
_MSG_DATA_DIR_STATE_PROMPT = _(
    "PostgreSQL data directory initialization state changed: {PREVIOUS} -> {CURRENT}.\n"
    "Choose: (a) abort  (c) continue\n"
)
_MSG_WIPE_DATA_PATH = _(
    "To use a different PostgreSQL data directory:\n"
    "1. Stop containers (docker compose down).\n"
    "2. Move or remove the old data under {PREVIOUS}.\n"
    "3. Run: odpm --accept-database-drift=data_path\n"
    "Current configured path: {CURRENT}."
)
_MSG_WIPE_POSTGRES_MAJOR = _(
    "To change PostgreSQL major version:\n"
    "1. Stop containers (docker compose down).\n"
    "2. Back up Odoo databases if needed.\n"
    "3. Remove the PostgreSQL data directory: {DATA_PATH}\n"
    "4. Run: odpm --accept-database-drift=postgres_major\n"
    "Alternatively delete {LAST_RUN_REL} and run odpm again."
)
_MSG_INVALID_CHOICE = _("Invalid choice. Please enter one of: {CHOICES}")


def accepted_drift_kinds(args: OdpmCliArgs) -> frozenset[str]:
    return frozenset(args.accept_database_drift)


def pending_resolution_drifts(config: Config) -> tuple[DatabaseDrift, ...]:
    report = collect_database_status(config)
    return drifts_requiring_resolution(report.drifts)


def unresolved_blocking_drifts(
    config: Config, args: OdpmCliArgs
) -> tuple[DatabaseDrift, ...]:
    accepted = accepted_drift_kinds(args)
    pending = pending_resolution_drifts(config)
    return tuple(
        drift
        for drift in pending
        if drift.severity == "high" and drift.kind not in accepted
    )


def ensure_no_blocking_database_drift(config: Config, args: OdpmCliArgs) -> None:
    blocking = unresolved_blocking_drifts(config, args)
    if not blocking:
        return
    kinds = ", ".join(drift.kind for drift in blocking)
    raise PipelineError(_MSG_STILL_BLOCKING.format(KINDS=kinds))


def _prompt_choice(prompt: str, valid: frozenset[str]) -> str:
    while True:
        choice = prompt_input(prompt).strip().lower()
        if choice in valid:
            return choice
        _logger.warning(
            _MSG_INVALID_CHOICE.format(CHOICES=", ".join(sorted(valid)))
        )


def _abort_resolution() -> None:
    raise PipelineError(_MSG_ABORTED)


def _accept_drift_baseline(
    config: Config,
    drift: DatabaseDrift,
    *,
    assume_app_role_present: bool = False,
) -> None:
    path = save_current_database_baseline(
        config, assume_app_role_present=assume_app_role_present
    )
    _logger.info(_MSG_BASELINE_UPDATED.format(PATH=path))


def _resolve_data_path(ctx: PrepareContext, drift: DatabaseDrift) -> None:
    prompt = _MSG_DATA_PATH_PROMPT.format(
        PREVIOUS=drift.previous, CURRENT=drift.current
    )
    choice = _prompt_choice(prompt, frozenset({"a", "b", "c"}))
    if choice == "a":
        _abort_resolution()
    if choice == "c":
        _logger.info(
            _MSG_WIPE_DATA_PATH.format(
                PREVIOUS=drift.previous, CURRENT=drift.current
            )
        )
        _abort_resolution()
    _accept_drift_baseline(ctx.config, drift)


def _resolve_postgres_major(ctx: PrepareContext, drift: DatabaseDrift) -> None:
    prompt = _MSG_POSTGRES_MAJOR_PROMPT.format(
        PREVIOUS=drift.previous, CURRENT=drift.current
    )
    choice = _prompt_choice(prompt, frozenset({"a", "b", "c"}))
    if choice == "a":
        _abort_resolution()
    if choice == "c":
        data_path = os.path.realpath(ctx.config.postgres_data_local_storage)
        _logger.info(
            _MSG_WIPE_POSTGRES_MAJOR.format(
                DATA_PATH=data_path,
                LAST_RUN_REL=constants.ODPM_DATABASE_LAST_RUN_REL_PATH,
            )
        )
        _abort_resolution()
    _accept_drift_baseline(ctx.config, drift)


def _resolve_app_role_missing(ctx: PrepareContext, drift: DatabaseDrift) -> None:
    prompt = _MSG_APP_ROLE_PROMPT.format(ROLE=drift.current)
    choice = _prompt_choice(prompt, frozenset({"a", "b"}))
    if choice == "a":
        _abort_resolution()
    ensure_app_role(ctx.config)
    _logger.info(
        _("PostgreSQL application role {ROLE} is ready.").format(ROLE=drift.current)
    )
    _accept_drift_baseline(ctx.config, drift, assume_app_role_present=True)


def _resolve_continue_or_abort(
    ctx: PrepareContext, drift: DatabaseDrift, *, prompt_template: str
) -> None:
    prompt = prompt_template.format(PREVIOUS=drift.previous, CURRENT=drift.current)
    choice = _prompt_choice(prompt, frozenset({"a", "c"}))
    if choice == "a":
        _abort_resolution()
    _accept_drift_baseline(ctx.config, drift)


def _resolve_interactive(ctx: PrepareContext, drift: DatabaseDrift) -> None:
    _logger.warning(format_database_drift_warning(drift))
    if drift.kind == "data_path":
        _resolve_data_path(ctx, drift)
    elif drift.kind == "postgres_major":
        _resolve_postgres_major(ctx, drift)
    elif drift.kind == "app_role_missing":
        _resolve_app_role_missing(ctx, drift)
    elif drift.kind == "odpm_scenario":
        _resolve_continue_or_abort(ctx, drift, prompt_template=_MSG_SCENARIO_PROMPT)
    elif drift.kind == "data_dir_empty_changed":
        _resolve_continue_or_abort(
            ctx, drift, prompt_template=_MSG_DATA_DIR_STATE_PROMPT
        )


def _non_interactive_error(pending: tuple[DatabaseDrift, ...]) -> str:
    kinds = ", ".join(drift.kind for drift in pending)
    return _MSG_NON_INTERACTIVE.format(KINDS=kinds)


def resolve_database_drifts(ctx: PrepareContext) -> None:
    accepted = accepted_drift_kinds(ctx.args)
    while True:
        pending = pending_resolution_drifts(ctx.config)
        if not pending:
            break
        drift = pending[0]
        if drift.kind in accepted:
            _logger.info(_MSG_ACCEPTED.format(KIND=drift.kind))
            _accept_drift_baseline(ctx.config, drift)
            continue
        if not stdin_is_interactive():
            raise PipelineError(_non_interactive_error(pending))
        _resolve_interactive(ctx, drift)
    ensure_no_blocking_database_drift(ctx.config, ctx.args)
