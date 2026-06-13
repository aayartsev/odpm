"""Host CLI flags and subparser for odpm plan."""

from __future__ import annotations

import argparse

from . import params


def add_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.PLAN_PARAM,
        help="""Show planned prepare/runtime steps without git pull, file writes, or docker compose up. Deprecated: use "odpm plan".""",
        action="store_true",
    )

    parser.add_argument(
        params.PLAN_NO_DOCKER_PARAM,
        help="""With odpm plan: skip docker compose ps/inspect probe; compose.up will not predict --force-recreate.""",
        action="store_true",
    )

    parser.add_argument(
        params.PLAN_SHOW_DIFF_PARAM,
        help="""With odpm plan: show unified diffs for generated project files (runtime config, compose, dockerignore).""",
        action="store_true",
    )

    parser.add_argument(
        params.PLAN_FORMAT_PARAM,
        help="""With odpm plan: output format for the plan (table or json).""",
        choices=["table", "json"],
        default="table",
    )

    parser.add_argument(
        params.PLAN_STRICT_PARAM,
        help="""With odpm plan: exit with code 1 when any required step would run or update.""",
        action="store_true",
    )


def register_plan_subparser(
    command_subparsers,
    common_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    return command_subparsers.add_parser(
        params.PLAN_SUBCOMMAND,
        parents=[common_parser],
        help="""Dry-run: show planned prepare/runtime steps. Example: odpm plan --skip-start""",
        description="Preview prepare and runtime steps without git materialization, file writes, or docker compose up.",
    )
