#!/usr/bin/env python3
"""Write ``dev_project/build_meta.json`` from the current git HEAD.

Used by package builds (deb / rpm / wheel) so installed ``odpm --version`` can
show the same ``(short_sha, YYYY-MM-DD)`` stamp as a git checkout.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _git_stdout(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"git {' '.join(args)} failed in {repo}: "
            f"{(completed.stderr or completed.stdout or '').strip()}"
        )
    text = (completed.stdout or "").strip()
    if not text:
        raise SystemExit(f"git {' '.join(args)} returned empty output in {repo}")
    return text


def write_build_meta(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parent.parent
    short_sha = _git_stdout(root, "rev-parse", "--short", "HEAD")
    commit_date = _git_stdout(root, "show", "-s", "--format=%cs", "HEAD")
    out_path = root / "dev_project" / "build_meta.json"
    payload = {"short_sha": short_sha, "commit_date": commit_date}
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    repo = Path(args[0]).resolve() if args else None
    path = write_build_meta(repo)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
