"""Host CLI argparse facade: build parser tree and parse argv."""

from __future__ import annotations

import argparse
import sys

from . import params
from .args import OdpmCliArgs
from .args_common import add_legacy_root_arguments
from .args_database import register_database_subparser
from .args_global import add_global_arguments
from .args_manifest import register_manifest_subparser
from .args_modules import register_modules_subparser
from .args_plan import register_plan_subparser
from .args_run import register_run_subparser
from .args_scaffold import register_scaffold_subparser
from .args_verbs import (
    register_build_subparser,
    register_init_subparser,
    register_prepare_subparser,
    register_up_subparser,
)
from .normalize import CliNormalizeError, normalize_cli_args


def build_arg_parser() -> argparse.ArgumentParser:
    global_parser = argparse.ArgumentParser(add_help=False)
    add_global_arguments(global_parser)

    parser = argparse.ArgumentParser(
        prog="odpm",
        description="Odoo Developer Project Manager",
        epilog="Developing is not configuration",
        parents=[global_parser],
    )
    add_legacy_root_arguments(parser)

    command_subparsers = parser.add_subparsers(dest="command", help="Commands")
    register_up_subparser(command_subparsers, global_parser)
    register_prepare_subparser(command_subparsers, global_parser)
    register_init_subparser(command_subparsers, global_parser)
    register_build_subparser(command_subparsers, global_parser)
    register_plan_subparser(command_subparsers, global_parser)
    register_database_subparser(command_subparsers, global_parser)
    register_manifest_subparser(command_subparsers, global_parser)
    register_modules_subparser(command_subparsers, global_parser)
    register_run_subparser(command_subparsers, global_parser)
    register_scaffold_subparser(command_subparsers)
    return parser


arg_parser = build_arg_parser()


def parse_args(argv: list[str] | None = None):
    if argv is None:
        argv = sys.argv[1:]
    argv_list = list(argv)
    if params.PLAN_PARAM in argv_list:
        from ...logging import get_module_logger  # noqa: PLC0415  # optional

        get_module_logger(__name__).warning(
            '%s is deprecated; use "odpm plan" instead.',
            params.PLAN_PARAM,
        )
    namespace = arg_parser.parse_args(argv_list)
    if getattr(namespace, "command", None) == params.PLAN_SUBCOMMAND:
        namespace.plan = True
    return namespace


def parse_cli_args(argv: list[str] | None = None) -> OdpmCliArgs:
    raw = OdpmCliArgs.from_namespace(parse_args(argv))
    try:
        normalized, warning = normalize_cli_args(raw)
    except CliNormalizeError as exc:
        from ...logging import get_module_logger  # noqa: PLC0415  # optional

        get_module_logger(__name__).error("%s", exc)
        raise SystemExit(2) from exc
    if warning:
        from ...logging import get_module_logger  # noqa: PLC0415  # optional

        get_module_logger(__name__).warning("%s", warning)
    return normalized
