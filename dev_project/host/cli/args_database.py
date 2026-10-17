"""Host CLI subparser for odpm database (host ops and stack ops)."""

from __future__ import annotations

import argparse

from . import params
from .args_database_policy import add_database_policy_arguments


def _add_stack_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.NO_GIT_UPDATE_PARAM,
        help="""Skip git clone, fetch, and checkout. Requires existing local repositories.""",
        action="store_true",
    )
    add_database_policy_arguments(parser)


def register_database_subparser(
    command_subparsers,
    global_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.DATABASE_SUBCOMMAND,
        parents=[global_parser],
        help=(
            "PostgreSQL host tools, or stack ops (backup/restore/drop/list). "
            "Example: odpm database status"
        ),
        description=(
            "Host: status, ensure-role, pull. "
            "Stack (prepare + compose up + container): backup, restore, drop, list. "
            "For restore with module install use: odpm up -d … --db-restore … -i …"
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

    list_parser = database_subparsers.add_parser(
        params.DATABASE_LIST_SUBCOMMAND,
        help="""List Odoo databases inside the running stack (prepare + compose up).""",
    )
    _add_stack_shared_arguments(list_parser)

    backup_parser = database_subparsers.add_parser(
        params.DATABASE_BACKUP_SUBCOMMAND,
        help="""Backup database (-d) via the stack. Optional archive name under BACKUP_DIR.""",
    )
    backup_parser.add_argument(
        params.D_PARAM,
        dest="d",
        required=True,
        type=str,
        help="""Database name to back up.""",
    )
    backup_parser.add_argument(
        "db_backup",
        nargs="?",
        default=True,
        help="""Optional archive name relative to BACKUP_DIR.""",
    )
    _add_stack_shared_arguments(backup_parser)

    restore_parser = database_subparsers.add_parser(
        params.DATABASE_RESTORE_SUBCOMMAND,
        help="""Restore archive into database (-d) via the stack. For -i/-u use odpm up.""",
    )
    restore_parser.add_argument(
        params.D_PARAM,
        dest="d",
        required=True,
        type=str,
        help="""Target database name.""",
    )
    restore_parser.add_argument(
        "db_restore",
        metavar="ARCHIVE",
        type=str,
        help="""Archive name relative to BACKUP_DIR.""",
    )
    _add_stack_shared_arguments(restore_parser)

    drop_parser = database_subparsers.add_parser(
        params.DATABASE_DROP_SUBCOMMAND,
        help="""Drop database (-d) via the stack.""",
    )
    drop_parser.add_argument(
        params.D_PARAM,
        dest="d",
        required=True,
        type=str,
        help="""Database name to drop.""",
    )
    _add_stack_shared_arguments(drop_parser)

    return parser
