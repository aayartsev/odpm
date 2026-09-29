"""Host CLI subparser for odpm run."""

from __future__ import annotations

import argparse

from . import params


def register_run_subparser(
    command_subparsers,
    common_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.RUN_SUBCOMMAND,
        parents=[common_parser],
        help="""Run a named recipe (re-exec odpm steps). Example: odpm run --list""",
        description=(
            "Execute a phased recipe of odpm invocations. "
            "Builtin apply-modules-from-diff is intended for server deploys."
        ),
    )
    parser.add_argument(
        params.RUN_RECIPE_DEST,
        nargs="?",
        default=None,
        help="""Recipe name (omit with --list).""",
    )
    parser.add_argument(
        params.RUN_LIST_PARAM,
        dest="run_list",
        action="store_true",
        help="""List available recipes and exit.""",
    )
    parser.add_argument(
        params.RUN_DRY_RUN_PARAM,
        dest="run_dry_run",
        action="store_true",
        help="""Print planned odpm argv; execute only steps marked for dry-run capture.""",
    )
    parser.add_argument(
        params.RUN_DIFF_BASE_PARAM,
        dest="run_diff_base",
        default=None,
        metavar="REF",
        help="""Pass-through baseline for recipes that support diff_base (e.g. apply-modules-from-diff).""",
    )
    parser.add_argument(
        params.RUN_REMOTE_URL_PARAM,
        dest="run_remote_url",
        default=None,
        metavar="URL",
        help="""Remote Odoo base URL for recipes that support url (e.g. pull-remote-db).""",
    )
    parser.add_argument(
        params.RUN_REMOTE_DB_PARAM,
        dest="run_remote_db",
        default=None,
        metavar="NAME",
        help="""Remote database name for recipes that support remote_db (e.g. pull-remote-db).""",
    )
    return parser
