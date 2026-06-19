"""Manifest ``database`` block → host ``db_creation_data`` overrides."""

from __future__ import annotations

from typing import Any


def database_creation_overrides_from_manifest(
    source_raw: dict[str, Any],
) -> dict[str, Any]:
    """Map manifest ``database.language`` / ``database.country`` to flat keys."""
    database = source_raw.get("database")
    if not isinstance(database, dict):
        return {}

    overrides: dict[str, Any] = {}
    if "language" in database:
        language = database["language"]
        if language is not None and str(language).strip():
            overrides["db_lang"] = str(language)
    if "country" in database:
        overrides["db_country_code"] = database["country"]
    return overrides


def merge_db_creation_from_manifest(
    db_creation_data: dict[str, Any],
    source_raw: dict[str, Any],
) -> dict[str, Any]:
    """Apply manifest database overrides on top of user_settings values."""
    overrides = database_creation_overrides_from_manifest(source_raw)
    if not overrides:
        return db_creation_data
    merged = dict(db_creation_data)
    merged.update(overrides)
    return merged
