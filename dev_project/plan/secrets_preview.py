"""Secrets materialize preview for odpm plan step evaluation."""

from __future__ import annotations

import os
from pathlib import Path

from ..project_env.secrets import (
    format_secrets_json,
    normalize_secrets_payload,
    read_secrets_source,
    secrets_runtime_path,
    secrets_source_is_gitignored,
    secrets_source_path,
)


def secrets_source_key_count(project_dir: str) -> int:
    secrets = read_secrets_source(project_dir)
    if secrets is None:
        return 0
    return len(secrets)


def secrets_needs_update(project_dir: str) -> tuple[bool, str]:
    secrets = read_secrets_source(project_dir)
    runtime_path = secrets_runtime_path(project_dir)
    if secrets is None:
        if os.path.isfile(runtime_path):
            return True, "remove stale runtime secrets"
        return False, "no secrets source"
    expected = format_secrets_json(normalize_secrets_payload(secrets))
    if not os.path.isfile(runtime_path):
        return True, "runtime secrets missing"
    on_disk = Path(runtime_path).read_text(encoding="utf-8")
    if on_disk != expected:
        return True, "secrets source changed"
    return False, "secrets runtime up to date"


def secrets_gitignore_warning(project_dir: str) -> str | None:
    if not os.path.isfile(secrets_source_path(project_dir)):
        return None
    if secrets_source_is_gitignored(project_dir):
        return None
    return (
        ".odpm/secrets.json exists but is not listed in .odpm/.gitignore; "
        "risk of accidental commit"
    )
