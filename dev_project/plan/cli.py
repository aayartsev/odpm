"""CLI helpers for odpm plan / command modes."""

from __future__ import annotations

from ..host.cli import params as cli_params
from ..host.cli.args import OdpmCliArgs


def is_plan_mode(args: OdpmCliArgs) -> bool:
    if args.plan:
        return True
    return args.command == cli_params.PLAN_SUBCOMMAND


def is_database_host_mode(args: OdpmCliArgs) -> bool:
    return (
        args.command == cli_params.DATABASE_SUBCOMMAND
        and args.database_subcommand in cli_params.DATABASE_HOST_SUBCOMMANDS
    )


def is_database_stack_mode(args: OdpmCliArgs) -> bool:
    return (
        args.command == cli_params.DATABASE_SUBCOMMAND
        and args.database_subcommand in cli_params.DATABASE_STACK_SUBCOMMANDS
    )


def is_database_mode(args: OdpmCliArgs) -> bool:
    """True for any ``odpm database`` command (host or stack)."""
    return args.command == cli_params.DATABASE_SUBCOMMAND


def is_manifest_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.MANIFEST_SUBCOMMAND


def is_modules_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.MODULES_SUBCOMMAND


def is_run_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.RUN_SUBCOMMAND


def is_up_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.UP_SUBCOMMAND


def is_prepare_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.PREPARE_SUBCOMMAND


def is_init_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.INIT_SUBCOMMAND


def is_build_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.BUILD_SUBCOMMAND


def is_scaffold_mode(args: OdpmCliArgs) -> bool:
    return args.command == cli_params.SCAFFOLD_SUBPARSER_PARAM
