"""Host CLI flags: prepare/runtime control (skip-start, git skip, lock file)."""

from __future__ import annotations

import argparse

from . import params


def add_compose_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.SKIP_START_PARAM,
        help="""Will generate docker-compose.yaml and exit without lounching odoo instance. After this command you can start instace with "docker compose up -d" for example""",
        nargs="?",
        default=None,
        const=True,
        type=bool,
    )

    parser.add_argument(
        params.NO_GIT_UPDATE_PARAM,
        help="""Skip git clone, fetch, and checkout. Requires existing local platform and developing project directories (use with --skip-start to regenerate Docker files offline).""",
        action="store_true",
    )

    parser.add_argument(
        params.UPDATE_LOCK_PARAM,
        help="""Resolve platform, developing (remote git), and full OCA-resolved dependency repositories, write .odpm/deps.lock.json, and exit without starting containers.""",
        action="store_true",
    )

    parser.add_argument(
        params.ODOO_BIN_PARAM,
        nargs=argparse.REMAINDER,
        help="""Command to pass through as a single string""",
    )
