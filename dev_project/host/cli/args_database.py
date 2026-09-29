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
        help=(
            "Local PostgreSQL status/roles, or pull a remote Odoo manager backup. "
            "Example: odpm database status"
        ),
        description=(
            "Inspect local PostgreSQL configuration, ensure the app role, "
            "or download a zip backup from a remote Odoo database manager."
        ),
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
    pull_parser = database_subparsers.add_parser(
        params.DATABASE_PULL_SUBCOMMAND,
        help=(
            "Download a zip backup from a remote Odoo /web/database/backup "
            "into BACKUP_DIR (master password via ODPM_REMOTE_DB_MASTER_PWD)."
        ),
    )
    pull_parser.add_argument(
        params.DATABASE_PULL_URL_PARAM,
        dest="database_pull_url",
        required=True,
        metavar="URL",
        help="""Base URL of the remote Odoo instance (https://host[:port]).""",
    )
    pull_parser.add_argument(
        params.DATABASE_PULL_REMOTE_DB_PARAM,
        dest="database_pull_remote_db",
        required=True,
        metavar="NAME",
        help="""Remote database name passed to the Odoo manager backup form.""",
    )
    return parser
