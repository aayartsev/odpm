"""Host CLI handlers for odpm database subcommands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _
from .ensure_role import ensure_app_role
from .status import (
    collect_database_status,
    format_database_status_json,
    format_database_status_table,
)

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs

_logger = get_module_logger(__name__)


def run_database_command(cli_args: OdpmCliArgs, config: Config) -> int:
    subcommand = cli_args.database_subcommand
    if subcommand == "status":
        return _run_database_status(cli_args, config)
    if subcommand == "ensure-role":
        return _run_database_ensure_role(config)
    raise ConfigError(
        _('database subcommand required: use "odpm database status" or '
          '"odpm database ensure-role".')
    )


def _run_database_status(cli_args: OdpmCliArgs, config: Config) -> int:
    report = collect_database_status(config)
    if cli_args.database_status_format == "json":
        print(format_database_status_json(report), end="", flush=True)
    else:
        _logger.info(format_database_status_table(report))
    return 0


def _run_database_ensure_role(config: Config) -> int:
    result = ensure_app_role(config)
    if result.outcome == "created":
        _logger.info(
            _("Created PostgreSQL application role {ROLE}.").format(ROLE=result.role)
        )
    else:
        _logger.info(
            _("Updated PostgreSQL application role {ROLE}.").format(ROLE=result.role)
        )
    return 0
