#!/usr/bin/env python3
"""Fail when a git tag version does not match dev_project.constants.RELEASE_VERSION."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dev_project.constants import RELEASE_VERSION


def verify_release_tag_version(tag_version: str) -> None:
    expected = RELEASE_VERSION.strip()
    actual = tag_version.strip()
    if actual != expected:
        raise ValueError(
            f"Tag version {actual!r} does not match "
            f"RELEASE_VERSION {expected!r} in dev_project/constants/scenarios.py"
        )


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(
            f"usage: {Path(__file__).name} TAG_VERSION",
            file=sys.stderr,
        )
        return 2
    try:
        verify_release_tag_version(args[0])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
