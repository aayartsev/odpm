"""Stable subprocess invocation for odpm CLI smoke tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def odpm_command(*argv: str) -> list[str]:
    """Argv prefix that runs odpm without requiring a legacy ``odpm.py`` wrapper."""
    return [sys.executable, "-m", "dev_project.cli", *argv]


def odpm_subprocess_env(
    *,
    cwd: str | os.PathLike[str],
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Environment for subprocess odpm runs (repo on ``PYTHONPATH``, ``PWD`` aligned)."""
    env = os.environ.copy()
    root = str(repo_root())
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        root if not existing_pythonpath else f"{root}{os.pathsep}{existing_pythonpath}"
    )
    env["PWD"] = str(cwd)
    if extra:
        env.update(extra)
    return env


def run_odpm(
    *argv: str,
    cwd: str | os.PathLike[str],
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Run odpm CLI in a subprocess and return the completed process."""
    merged_env = odpm_subprocess_env(cwd=cwd, extra=env)
    return subprocess.run(
        odpm_command(*argv),
        cwd=cwd,
        env=merged_env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
