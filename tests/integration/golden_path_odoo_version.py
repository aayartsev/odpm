"""Read ``odoo_version`` from a golden-path project ``odpm.json`` for HTTP probes."""

from __future__ import annotations

import json
from pathlib import Path


def odoo_version_from_project(project: Path) -> str | None:
    """Return ``odoo_version`` from ``odpm.json`` or ``developing/odpm.json``."""
    for rel in ("odpm.json", "developing/odpm.json"):
        path = project / rel
        if not path.is_file():
            continue
        try:
            version = json.loads(path.read_text(encoding="utf-8")).get("odoo_version")
        except (OSError, json.JSONDecodeError):
            continue
        if version:
            return str(version)
    return None


def odoo_major_from_version(version: str | None) -> int | None:
    """``19.0`` / ``20`` → major int; invalid → ``None``."""
    if not version:
        return None
    major_text = str(version).strip().split(".", 1)[0]
    if not major_text.isdigit():
        return None
    return int(major_text)


def golden_path_http_probe(major: int | None) -> tuple[str, set[int]]:
    """
    HTTP path and accepted status codes for golden-path readiness.

    Driven by ``odpm.json`` ``odoo_version`` major:
    - Odoo **20+**: probe ``/web/login`` (unauthenticated ``/web`` may return 403).
    - Older / unknown: probe ``/web`` and accept 200 or redirect 303.
    """
    if major is not None and major >= 20:
        return "/web/login", {200}
    return "/web", {200, 303}
