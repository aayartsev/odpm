"""Extras requirements stamp and pip -r sync helpers for fresh venv mode."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
except ImportError:
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.utils import canonicalize_name


@dataclass(frozen=True)
class ExtrasLockState:
    stamp: str
    distributions: list[str]


def managed_distribution_names(requirements_txt: list[str]) -> list[str]:
    names: list[str] = []
    for requirement in requirements_txt:
        line = requirement.strip()
        if not line:
            continue
        names.append(canonicalize_name(Requirement(line).name))
    return sorted(set(names))


def read_extras_lock(path: str) -> ExtrasLockState | None:
    if not os.path.isfile(path):
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    stamp = payload.get("stamp")
    distributions = payload.get("distributions")
    if not isinstance(stamp, str) or not stamp.strip():
        return None
    if not isinstance(distributions, list):
        return None
    cleaned = sorted(
        {
            str(name).strip()
            for name in distributions
            if isinstance(name, str) and name.strip()
        }
    )
    return ExtrasLockState(stamp=stamp.strip(), distributions=cleaned)


def write_extras_lock(path: str, *, stamp: str, distributions: list[str]) -> None:
    payload = {
        "stamp": stamp,
        "distributions": sorted(set(distributions)),
    }
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_extras_requirements_file(path: str, requirements_txt: list[str]) -> None:
    lines = [req.strip() for req in requirements_txt if req and req.strip()]
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
