"""Shared host CLI flags attached to the common argument parser parent."""

from __future__ import annotations

import argparse

from .args_compose import add_compose_arguments
from .args_database_policy import add_database_policy_arguments
from .args_db import add_db_arguments
from .args_init import add_init_core_arguments, add_platform_env_arguments
from .args_plan import add_plan_arguments


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    # Registration order matches the pre-R-5 monolithic parse_args.py (--help layout).
    add_init_core_arguments(parser)
    add_db_arguments(parser)
    add_platform_env_arguments(parser)
    add_plan_arguments(parser)
    add_database_policy_arguments(parser)
    add_compose_arguments(parser)
