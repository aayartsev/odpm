"""Host CLI subparser for odpm modules."""

from __future__ import annotations

import argparse

from . import params


def register_modules_subparser(
    command_subparsers,
    common_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.MODULES_SUBCOMMAND,
        parents=[common_parser],
        help="""Classify Odoo modules from git history. Example: odpm modules diff""",
        description=(
            "Compute init/update module lists from the developing git repo, "
            "or record the last applied developing SHA."
        ),
    )
    modules_subparsers = parser.add_subparsers(
        dest="modules_subcommand",
        help="Modules commands",
        required=True,
    )
    diff_parser = modules_subparsers.add_parser(
        params.MODULES_DIFF_SUBCOMMAND,
        help="""List modules to init/update since a git baseline.""",
    )
    diff_parser.add_argument(
        params.MODULES_DIFF_BASE_PARAM,
        dest="modules_diff_base",
        default=None,
        metavar="REF",
        help=(
            """Git baseline (sha/tag/branch) or @last-applied. Default: ODPM_DIFF_BASE, """
            """then CI_MERGE_REQUEST_DIFF_BASE_SHA, then deploy marker if present."""
        ),
    )
    diff_parser.add_argument(
        params.MODULES_DIFF_FORMAT_PARAM,
        dest="modules_diff_format",
        choices=["text", "shell", "json"],
        default="text",
        help="""Output format (default: text).""",
    )
    modules_subparsers.add_parser(
        params.MODULES_RECORD_APPLIED_SUBCOMMAND,
        help="""Write .odpm/deploy/last_applied.json from developing HEAD.""",
    )
    return parser
