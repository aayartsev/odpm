"""Test helpers for host CLI arguments."""

from __future__ import annotations

from dev_project.host.cli.args import OdpmCliArgs


def cli_args(**kwargs) -> OdpmCliArgs:
    return OdpmCliArgs(**kwargs)
