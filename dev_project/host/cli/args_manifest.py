"""Host CLI subparser for odpm manifest."""

from __future__ import annotations

import argparse

from . import params


def register_manifest_subparser(
    command_subparsers,
    common_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.MANIFEST_SUBCOMMAND,
        parents=[common_parser],
        help="""Migrate or validate project manifest. Example: odpm manifest validate""",
        description="Migrate or validate odpm.json manifest schema.",
    )
    manifest_subparsers = parser.add_subparsers(
        dest="manifest_subcommand",
        help="Manifest commands",
        required=True,
    )
    migrate_parser = manifest_subparsers.add_parser(
        params.MANIFEST_MIGRATE_SUBCOMMAND,
        help="""Show v1→v2 migration diff or write nested manifest v2.""",
    )
    migrate_parser.add_argument(
        params.MANIFEST_MIGRATE_WRITE_PARAM,
        dest="manifest_migrate_write",
        action="store_true",
        help="""Write migrated manifest v2 to the developing project odpm.json.""",
    )
    manifest_subparsers.add_parser(
        params.MANIFEST_VALIDATE_SUBCOMMAND,
        help="""Validate odpm.json against packaged JSON Schema (read-only).""",
    )
    return parser
