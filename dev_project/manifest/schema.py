"""JSON Schema validation for odpm.json manifest v2."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..errors import ConfigError
from ..translations import _

_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


@lru_cache(maxsize=1)
def manifest_schema_v1() -> dict:
    with (_SCHEMAS_DIR / "odpm_manifest.v1.json").open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


@lru_cache(maxsize=1)
def manifest_schema_v2() -> dict:
    with (_SCHEMAS_DIR / "odpm_manifest.v2.json").open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


def validate_manifest_v2(raw: dict) -> None:
    """Raise :class:`ConfigError` when *raw* does not match manifest v2 schema."""
    import jsonschema
    from jsonschema.exceptions import ValidationError

    try:
        jsonschema.validate(raw, manifest_schema_v2())
    except ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "(root)"
        message = _(
            "Invalid manifest v2 odpm.json at {PATH}: {DETAIL}"
        ).format(PATH=path, DETAIL=exc.message)
        raise ConfigError(message) from exc
