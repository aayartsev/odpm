"""Helpers for interactive vs non-interactive host CLI."""

from __future__ import annotations

import sys

from .errors import ConfigError
from .translations import _


def stdin_is_interactive() -> bool:
    return sys.stdin.isatty()


def prompt_input(prompt: str) -> str:
    if not stdin_is_interactive():
        raise ConfigError(
            _("Interactive input is not available in non-interactive mode.")
        )
    return input(prompt)
