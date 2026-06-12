"""Run pre-commit in the developing project directory (exec-form compose entrypoint)."""

from __future__ import annotations

import sys

from ..subprocess_runner import run_logged
from .exceptions import ContainerError


def parse_project_dir(argv: list[str] | None = None) -> str:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--" in args:
        separator_index = args.index("--")
        rest = args[separator_index + 1 :]
    else:
        rest = args
    if len(rest) != 1 or not rest[0].strip():
        raise ContainerError(
            "Expected exactly one project directory after '--' "
            "(developing project path inside the container)"
        )
    return rest[0]


def _ensure_git_safe_directory(path: str, *, cwd: str) -> None:
    git_exit = run_logged(
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
    if git_exit != 0:
        raise ContainerError(
            f"git config safe.directory failed for {path!r} (exit {git_exit})"
        )


def run_pre_commit(project_dir: str) -> None:
    # Wildcard: pre-commit hook clones under ~/.cache/pre-commit (bind-mounted).
    _ensure_git_safe_directory("*", cwd=project_dir)
    _ensure_git_safe_directory(project_dir, cwd=project_dir)

    pre_commit_exit = run_logged(
        ["pre-commit", "run", "--all-files"],
        cwd=project_dir,
    )
    if pre_commit_exit != 0:
        raise SystemExit(pre_commit_exit)


def main() -> None:
    try:
        run_pre_commit(parse_project_dir())
    except ContainerError as exc:
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
