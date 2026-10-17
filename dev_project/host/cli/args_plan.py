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
    global_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.PLAN_SUBCOMMAND,
        parents=[global_parser],
        help="""Dry-run: show planned prepare/runtime steps. Example: odpm plan""",
        description="Preview prepare and runtime steps without git materialization, file writes, or docker compose up.",
    )
    parser.add_argument(
        params.PLAN_NO_DOCKER_PARAM,
        help="""Skip docker compose ps/inspect probe; compose.up will not predict --force-recreate.""",
        action="store_true",
    )
    parser.add_argument(
        params.PLAN_SHOW_DIFF_PARAM,
        help="""Show unified diffs for generated project files.""",
        action="store_true",
    )
    parser.add_argument(
        params.PLAN_FORMAT_PARAM,
        help="""Output format for the plan (table or json).""",
        choices=["table", "json"],
        default="table",
    )
    parser.add_argument(
        params.PLAN_STRICT_PARAM,
        help="""Exit with code 1 when any required step would run or update.""",
        action="store_true",
    )
    parser.add_argument(
        params.SKIP_START_PARAM,
        help="""Preview as if prepare-only (no compose up).""",
        nargs="?",
        default=None,
        const=True,
        type=bool,
    )
    parser.add_argument(
        params.NO_GIT_UPDATE_PARAM,
        help="""Preview with git steps skipped.""",
        action="store_true",
    )
    parser.add_argument(
        params.UPDATE_LOCK_PARAM,
        help="""Preview as if writing deps.lock.json.""",
        action="store_true",
    )
    parser.add_argument(
        params.SYNC_MANIFEST_LOCKS_PARAM,
        help="""Preview as if syncing locks.git into odpm.json.""",
        action="store_true",
    )
    return parser
