"""User-facing ``odpm --version`` string, optionally enriched from git."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .. import constants

import dev_project


def _candidate_roots(program_dir: str | None) -> list[Path]:
    roots: list[Path] = []
    if program_dir:
        roots.append(Path(program_dir).resolve())
    package_parent = Path(dev_project.__file__).resolve().parent.parent
    if package_parent not in roots:
        roots.append(package_parent)
    return roots


def find_git_work_tree(program_dir: str | None = None) -> Path | None:
    """Return a git work tree that contains the installed odpm sources, if any."""
    seen: set[Path] = set()
    for start in _candidate_roots(program_dir):
        current = start
        while current not in seen:
            seen.add(current)
            if (current / ".git").exists():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
    return None


def _git_stdout(repo: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    text = (completed.stdout or "").strip()
    return text or None


def read_git_build_meta(program_dir: str | None = None) -> tuple[str, str] | None:
    """Return ``(short_sha, YYYY-MM-DD)`` for HEAD, or ``None`` if unavailable."""
    repo = find_git_work_tree(program_dir)
    if repo is None:
        return None
    short_sha = _git_stdout(repo, "rev-parse", "--short", "HEAD")
    commit_date = _git_stdout(repo, "show", "-s", "--format=%cs", "HEAD")
    if not short_sha or not commit_date:
        return None
    return short_sha, commit_date


def format_odpm_version_line(program_dir: str | None = None) -> str:
    """Build the ``odpm --version`` log line.

    Example with git: ``odpm version: 4.8.0-dev (87564d8, 2026-09-28)``.
    Without git metadata: ``odpm version: 4.8.0-dev``.
    """
    line = f"{constants.PROJECT_NAME} version: {constants.ODPM_VERSION}"
    meta = read_git_build_meta(program_dir)
    if meta is None:
        return line
    short_sha, commit_date = meta
    return f"{line} ({short_sha}, {commit_date})"
