"""Build argv prefix for re-executing odpm as a subprocess."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ..errors import ConfigError
from ..translations import _

RECIPE_DEPTH_ENV = "ODPM_RECIPE_DEPTH"
MAX_RECIPE_DEPTH = 1


def odpm_argv_prefix() -> list[str]:
    """Return argv prefix that launches odpm host CLI."""
    argv0 = Path(sys.argv[0]).name if sys.argv else ""
    if argv0 in {"odpm", "odpm.py"}:
        return [sys.argv[0]]
    return [sys.executable, "-m", "dev_project.cli"]


def full_odpm_argv(step_argv: list[str] | tuple[str, ...]) -> list[str]:
    return [*odpm_argv_prefix(), *step_argv]


def guard_step_argv(step_argv: list[str] | tuple[str, ...]) -> None:
    if not step_argv:
        raise ConfigError(_("Recipe step argv must not be empty."))
    if step_argv[0] == "run":
        raise ConfigError(
            _("Recipe steps must not invoke 'odpm run' (recursion forbidden).")
        )


def current_recipe_depth(environ: dict[str, str] | None = None) -> int:
    env = environ if environ is not None else os.environ
    raw = str(env.get(RECIPE_DEPTH_ENV) or "0").strip() or "0"
    try:
        return int(raw)
    except ValueError:
        return 0


def child_environ(
    base: dict[str, str],
    *,
    depth: int,
) -> dict[str, str]:
    if depth > MAX_RECIPE_DEPTH:
        raise ConfigError(
            _("Recipe nesting exceeds maximum depth {MAX}.").format(MAX=MAX_RECIPE_DEPTH)
        )
    out = dict(base)
    out[RECIPE_DEPTH_ENV] = str(depth)
    return out
