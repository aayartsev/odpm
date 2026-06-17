"""Host CLI subparser for odpm database."""

from __future__ import annotations

import argparse

from . import params


def register_database_subparser(
    command_subparsers,
    common_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.DATABASE_SUBCOMMAND,
        parents=[common_parser],
        help="""Inspect or repair local PostgreSQL configuration. Example: odpm database status""",
        description="Show database configuration drift and live PostgreSQL health.",
    )
    database_subparsers = parser.add_subparsers(
        dest="database_subcommand",
        help="Database commands",
        required=True,
    )
    status_parser = database_subparsers.add_parser(
        params.DATABASE_STATUS_SUBCOMMAND,
        help="""Show static fingerprints, drift, and live postgres probes.""",
    )
    status_parser.add_argument(
        params.DATABASE_STATUS_FORMAT_PARAM,
        dest="database_status_format",
        choices=["table", "json"],
        default="table",
        help="""Output format for database status.""",
    )
    database_subparsers.add_parser(
        params.DATABASE_ENSURE_ROLE_SUBCOMMAND,
        help="""Create or update the Odoo application role inside PostgreSQL.""",
    )
    return parser
