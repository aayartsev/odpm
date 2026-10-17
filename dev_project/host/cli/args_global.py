"""Global host CLI flags shared by all odpm commands."""

from __future__ import annotations

import argparse

from . import params


def add_global_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.VERSION_SHORT,
        params.VERSION,
        dest="version",
        help="""Will show version of odpm manager""",
        action="store_true",
    )
    parser.add_argument(
        params.SECRETS_FILE_PARAM,
        help="""Import secrets from a JSON file into .odpm/secrets.json (schema v1). Works with --init and on any run.""",
        type=str,
    )
    parser.add_argument(
        params.SECRETS_PROVIDER_PARAM,
        help="""Secrets provider for this run (file, infisical, or a third-party plugin id). Overrides ODPM_SECRETS_PROVIDER and secrets.provider.type. --secrets-file implies file.""",
        type=str,
    )
    parser.add_argument(
        params.SECURITY_PROFILE_PARAM,
        help="""Security profile for this run (convenience or hardened). Overrides ODPM_SECURITY_PROFILE. Defaults from ODPM_SCENARIO (developer→convenience, server→hardened).""",
        type=str,
    )
