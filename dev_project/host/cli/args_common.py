"""Shared host CLI flag groups for odpm parsers."""

from __future__ import annotations

import argparse

from . import params
from .args_compose import add_compose_arguments
from .args_database_policy import add_database_policy_arguments
from .args_db import add_db_arguments
from .args_global import add_global_arguments
from .args_init import add_init_core_arguments, add_platform_env_arguments
from .args_plan import add_plan_arguments


def add_legacy_root_arguments(parser: argparse.ArgumentParser) -> None:
    """Flags kept on the root parser for 4.8 compatibility (no subcommand)."""
    add_init_core_arguments(parser)
    add_db_arguments(parser)
    add_platform_env_arguments(parser)
    add_plan_arguments(parser)
    add_database_policy_arguments(parser)
    add_compose_arguments(parser)


def add_up_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    """Runtime / database flags for ``odpm up``."""
    add_db_arguments(parser)
    add_database_policy_arguments(parser)
    parser.add_argument(
        params.NO_GIT_UPDATE_PARAM,
        help="""Skip git clone, fetch, and checkout. Requires existing local platform and developing project directories.""",
        action="store_true",
    )
    parser.add_argument(
        params.ODOO_BIN_PARAM,
        nargs=argparse.REMAINDER,
        help="""Command to pass through as a single string""",
    )


def add_prepare_arguments(parser: argparse.ArgumentParser) -> None:
    """Flags for ``odpm prepare`` (files only, no compose up)."""
    add_database_policy_arguments(parser)
    parser.add_argument(
        params.NO_GIT_UPDATE_PARAM,
        help="""Skip git clone, fetch, and checkout. Requires existing local platform and developing project directories.""",
        action="store_true",
    )
    parser.add_argument(
        params.UPDATE_LOCK_PARAM,
        help="""Resolve repositories, write .odpm/deps.lock.json, and exit without starting containers.""",
        action="store_true",
    )
    parser.add_argument(
        params.SYNC_MANIFEST_LOCKS_PARAM,
        help="""With --update-lock on manifest v2 (developer scenario), also write locks.git in odpm.json.""",
        action="store_true",
    )


# Re-export for callers that still expect the old name during transition.
__all__ = [
    "add_global_arguments",
    "add_legacy_root_arguments",
    "add_up_runtime_arguments",
    "add_prepare_arguments",
]
