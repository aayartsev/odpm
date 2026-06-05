"""Shared subprocess helpers for host-side odpm."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence


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
) -> CommandResult:
    result = subprocess.run(
        list(argv),
        cwd=cwd,
        capture_output=capture,
        text=capture,
    )
    if capture:
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )
    return CommandResult(returncode=result.returncode, stdout="", stderr="")


def run_logged(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
) -> int:
    return subprocess.run(list(argv), cwd=cwd).returncode
