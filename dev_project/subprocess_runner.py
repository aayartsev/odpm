"""Shared subprocess helpers for host-side odpm."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence

from .errors import SubprocessError


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def run_checked(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    capture: bool = True,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a subprocess and return the result without checking the exit code.

    Prefer :func:`run_or_raise` for commands that must succeed.
    """
    run_kwargs: dict = {"cwd": cwd, "capture_output": capture}
    if env is not None:
        run_kwargs["env"] = env
    if input_text is not None:
        run_kwargs["input"] = input_text
        run_kwargs["text"] = True
    elif capture:
        run_kwargs["text"] = True
    result = subprocess.run(list(argv), **run_kwargs)
    if capture:
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )
    return CommandResult(returncode=result.returncode, stdout="", stderr="")


def run_or_raise(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    capture: bool = True,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a subprocess and raise :class:`SubprocessError` when exit code is non-zero."""
    result = run_checked(argv, cwd=cwd, capture=capture, env=env)
    if result.returncode != 0:
        argv_list = list(argv)
        stderr = result.stderr.strip()
        message = f"Command failed (exit {result.returncode}): {' '.join(argv_list)}"
        if stderr:
            message = f"{message}: {stderr}"
        raise SubprocessError(
            message,
            argv=argv_list,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    return result


def run_logged(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> int:
    run_kwargs: dict = {"cwd": cwd}
    if env is not None:
        run_kwargs["env"] = env
    return subprocess.run(list(argv), **run_kwargs).returncode
