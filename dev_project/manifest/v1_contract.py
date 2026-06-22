"""Resolve flat v1 ``odpm_version`` contract line with legacy fallback."""

from __future__ import annotations

from typing import Any

from .. import constants
from ..logging import get_module_logger

_logger = get_module_logger(__name__)


def resolve_v1_manifest_contract_line(raw: dict[str, Any]) -> str:
    """Return v1 ``odpm_version`` contract line, warning on legacy missing field."""
    explicit = raw.get("odpm_version")
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()
    _logger.warning(
        "odpm.json is missing odpm_version; treating manifest contract as %s. "
        "Add odpm_version: %r to silence this warning (supported by manager %s).",
        constants.DEFAULT_ODPM_VERSION,
        constants.MANIFEST_V1_CONTRACT_LINE,
        constants.ODPM_VERSION,
    )
    return constants.DEFAULT_ODPM_VERSION
