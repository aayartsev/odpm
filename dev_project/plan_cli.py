"""CLI helpers for odpm plan / odpm plan subcommand."""

from __future__ import annotations

from .host_cli import params as cli_params
from .host_cli.args import OdpmCliArgs


def is_plan_mode(args: OdpmCliArgs) -> bool:
    if args.plan:
        return True
    return args.command == cli_params.PLAN_SUBCOMMAND
