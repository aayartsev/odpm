"""CLI helpers for odpm plan / odpm plan subcommand."""

from __future__ import annotations

from argparse import Namespace

from .host_cli import params as cli_params


def normalize_plan_argv(argv: list[str]) -> list[str]:
    if argv and argv[0] == cli_params.PLAN_SUBCOMMAND:
        return [cli_params.PLAN_PARAM, *argv[1:]]
    return argv


def is_plan_mode(args: Namespace) -> bool:
    return bool(getattr(args, "plan", False))
