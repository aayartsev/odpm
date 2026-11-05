"""Bake pre-commit hook environments into the lint CI image layer."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .logging import get_module_logger

_logger = get_module_logger(__name__)

_BAKE_GIT_NAME = "odpm-lint-bake"
_BAKE_GIT_EMAIL = "odpm-lint-bake@localhost"
_CONFIG_NAME = ".pre-commit-config.yaml"
_HOOKS_NAME = ".pre-commit-hooks.yaml"
# Isolated tree so git init never touches a foreign .git under WORKDIR (platform).
_BAKE_SUBDIR = ".odpm-lint-bake"


class BakePreCommitError(Exception):
    exit_code = 1


def _run(argv: list[str], *, cwd: str) -> int:
    completed = subprocess.run(list(argv), cwd=cwd, check=False)
    return completed.returncode


def _run_checked(argv: list[str], *, cwd: str) -> None:
    code = _run(argv, cwd=cwd)
    if code != 0:
        raise BakePreCommitError(
            f"command failed (exit {code}): {' '.join(argv)}"
        )


def _ensure_git_safe_directory(path: str, *, cwd: str) -> None:
    _run_checked(
        [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            path,
        ],
        cwd=cwd,
    )


def _prepare_bake_dir(root: Path) -> Path:
    """Copy pre-commit configs into an isolated bake directory under *root*."""
    config_path = root / _CONFIG_NAME
    if not config_path.is_file():
        raise BakePreCommitError(
            f"missing {_CONFIG_NAME} in {root} (required for lint bake)"
        )
    bake_dir = root / _BAKE_SUBDIR
    bake_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, bake_dir / _CONFIG_NAME)
    hooks_src = root / _HOOKS_NAME
    hooks_dst = bake_dir / _HOOKS_NAME
    if hooks_src.is_file():
        shutil.copy2(hooks_src, hooks_dst)
    elif hooks_dst.is_file():
        hooks_dst.unlink()
    return bake_dir


def _commit_if_staged(cwd: str) -> None:
    """Create one bake commit when the index has changes; skip if already baked."""
    staged = _run(["git", "diff", "--cached", "--quiet"], cwd=cwd)
    if staged == 0:
        _logger.info("No staged changes for lint bake commit; skipping commit")
        return
    if staged != 1:
        raise BakePreCommitError(
            f"git diff --cached --quiet failed (exit {staged})"
        )
    _run_checked(
        [
            "git",
            "-c",
            f"user.name={_BAKE_GIT_NAME}",
            "-c",
            f"user.email={_BAKE_GIT_EMAIL}",
            "commit",
            "-m",
            "odpm lint bake",
        ],
        cwd=cwd,
    )


def bake_pre_commit(workdir: str) -> None:
    root = Path(workdir).resolve()
    if not root.is_dir():
        raise BakePreCommitError(f"workdir is not a directory: {root}")

    bake_dir = _prepare_bake_dir(root)
    cwd = str(bake_dir)

    if not (bake_dir / ".git").exists():
        _run_checked(["git", "init"], cwd=cwd)

    to_add = [_CONFIG_NAME]
    if (bake_dir / _HOOKS_NAME).is_file():
        to_add.append(_HOOKS_NAME)
    _run_checked(["git", "add", "--", *to_add], cwd=cwd)
    _commit_if_staged(cwd)

    _ensure_git_safe_directory("*", cwd=cwd)
    _ensure_git_safe_directory(cwd, cwd=cwd)

    # Hook envs land under the container user's home (~/.cache/pre-commit).
    _logger.info("Running pre-commit install-hooks in %s", bake_dir)
    _run_checked(["pre-commit", "install-hooks"], cwd=cwd)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Bake pre-commit hooks for the lint CI image"
    )
    parser.add_argument(
        "--workdir",
        default=os.getcwd(),
        help="Directory with .pre-commit-config.yaml (default: cwd)",
    )
    args = parser.parse_args(argv)
    try:
        bake_pre_commit(args.workdir)
    except BakePreCommitError as exc:
        _logger.error("%s", exc)
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
