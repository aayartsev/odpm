"""Subparsers for odpm up / prepare / init / build."""

from __future__ import annotations

import argparse

from . import params
from .args_common import add_prepare_arguments, add_up_runtime_arguments
from .args_init import add_platform_env_arguments


def register_up_subparser(
    command_subparsers,
    global_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.UP_SUBCOMMAND,
        parents=[global_parser],
        help="Prepare project files and start the compose stack. Example: odpm up -d demo -i",
        description=(
            "Materialize project files and run docker compose up. "
            "Module install/update and combined db-restore flows use this command."
        ),
    )
    add_up_runtime_arguments(parser)
    return parser


def register_prepare_subparser(
    command_subparsers,
    global_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.PREPARE_SUBCOMMAND,
        parents=[global_parser],
        help="Prepare project files without starting containers. Example: odpm prepare -d test_db",
        description=(
            "Generate docker-compose and related files, then exit without compose up. "
            "Optional -d bakes the database name into the Odoo start command. "
            "Replaces legacy --skip-start."
        ),
    )
    add_prepare_arguments(parser)
    return parser


def register_init_subparser(
    command_subparsers,
    global_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.INIT_SUBCOMMAND,
        parents=[global_parser],
        help="Initialize a directory as an odpm project. Example: odpm init URL --branch 19.0",
        description="Clone or link a developing project and write initial odpm config.",
    )
    parser.add_argument(
        "init",
        metavar="URL",
        help="""Git URL or file:// path of the developing project""",
    )
    parser.add_argument(
        params.BRANCH_PARAM,
        help="""Branch of the git repository to clone""",
        type=str,
    )
    parser.add_argument(
        params.ODOO_VERSION,
        help="""Odoo version for the new project""",
        type=str,
    )
    add_platform_env_arguments(parser)
    # build-image flags are not part of init; avoid add_init_core (--init/--build-image)
    return parser


def register_build_subparser(
    command_subparsers,
    global_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.BUILD_SUBCOMMAND,
        parents=[global_parser],
        help="Build the CI image. Example: odpm build --image-tag my/image:tag",
        description=(
            "Build the final CI app image via layered stages "
            "(base → platform → optional deps → app; ADR-027)."
        ),
    )
    parser.add_argument(
        params.IMAGE_TAG_PARAM,
        help="Docker tag for the CI image",
        type=str,
    )
    parser.add_argument(
        params.IMAGE_BUILDER_PARAM,
        help="CI image build backend: docker (default) or kaniko",
        choices=["docker", "kaniko"],
        type=str,
    )
    parser.add_argument(
        params.IMAGE_PUSH_PARAM,
        help="After build, push the image (docker push / kaniko --destination)",
        action="store_true",
    )
    parser.add_argument(
        params.IMAGE_PRUNE_STALE_PARAM,
        dest="image_prune_stale",
        help=(
            "After each successful layer ensure, delete stale cache-* tags "
            "(same as ODPM_IMAGE_PRUNE_STALE=1)"
        ),
        action="store_true",
    )
    parser.add_argument(
        params.NO_GIT_UPDATE_PARAM,
        help="""Skip git clone, fetch, and checkout when sources already exist.""",
        action="store_true",
    )
    return parser
