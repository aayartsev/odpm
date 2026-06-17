"""Host CLI flags for database drift resolution policy."""

from __future__ import annotations

import argparse

from . import params


def add_database_policy_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.ACCEPT_DATABASE_DRIFT_PARAM,
        action="append",
        default=[],
        metavar="KIND",
        help=(
            "Accept database drift of KIND without a prompt (repeatable). "
            "Example: --accept-database-drift=data_path"
        ),
    )
