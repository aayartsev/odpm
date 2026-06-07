"""CLI helpers for odpm plan / odpm plan subcommand."""

from __future__ import annotations

from argparse import Namespace

from .host_cli import params as cli_params
from .host_cli.args import OdpmCliArgs, as_cli_args


def normalize_plan_argv(argv: list[str]) -> list[str]:
    """Legacy argv rewrite kept for compatibility; host parsing uses native ``plan`` subparser."""
    if argv and argv[0] == cli_params.PLAN_SUBCOMMAND:
        return [cli_params.PLAN_PARAM, *argv[1:]]
    return argv


def is_plan_mode(args: Namespace | OdpmCliArgs) -> bool:
    cli_args = as_cli_args(args)
    if cli_args.plan:
        return True
    return cli_args.command == cli_params.PLAN_SUBCOMMAND
