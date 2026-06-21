"""Host CLI argparse facade: build parser tree and parse argv."""

from __future__ import annotations

import argparse
import sys

from . import params
from .args_common import add_common_arguments
from .args_database import register_database_subparser
from .args_manifest import register_manifest_subparser
from .args_plan import register_plan_subparser
from .args_scaffold import register_scaffold_subparser


def build_arg_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    add_common_arguments(common_parser)

    parser = argparse.ArgumentParser(
        prog="odpm",
        description="Odoo Developer Project Manager",
        epilog="Developing is not configuration",
        parents=[common_parser],
    )

    command_subparsers = parser.add_subparsers(dest="command", help="Commands")
    register_plan_subparser(command_subparsers, common_parser)
    register_database_subparser(command_subparsers, common_parser)
    register_manifest_subparser(command_subparsers, common_parser)
    register_scaffold_subparser(command_subparsers)
    return parser


arg_parser = build_arg_parser()


def parse_args(argv: list[str] | None = None):
    if argv is None:
        argv = sys.argv[1:]
    argv_list = list(argv)
    if params.PLAN_PARAM in argv_list:
        from ...logging import get_module_logger

        get_module_logger(__name__).warning(
            '%s is deprecated; use "odpm plan" instead.',
            params.PLAN_PARAM,
        )
    namespace = arg_parser.parse_args(argv_list)
    if getattr(namespace, "command", None) == params.PLAN_SUBCOMMAND:
        namespace.plan = True
    return namespace


def parse_cli_args(argv: list[str] | None = None):
    from .args import OdpmCliArgs

    return OdpmCliArgs.from_namespace(parse_args(argv))
