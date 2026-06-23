"""Parse and validate debugger-related .env values."""

from __future__ import annotations

from ..logging import get_module_logger
from ..translations import _
from .constants import (
    DEBUGGER_BACKEND_VALUES,
    DEFAULT_DEBUGGER_BACKEND,
    DEFAULT_DEBUGGER_CONNECT_HOST,
    DEFAULT_ODPM_IDE,
    ODPM_IDE_VALUES,
)

_logger = get_module_logger(__name__)


def parse_debugger_backend(raw: str | None) -> str:
    value = (raw or "").strip() or DEFAULT_DEBUGGER_BACKEND
    if value not in DEBUGGER_BACKEND_VALUES:
        _logger.warning(
            _("Unknown ODPM_DEBUGGER_BACKEND=%r, using %s"),
            raw,
            DEFAULT_DEBUGGER_BACKEND,
        )
        return DEFAULT_DEBUGGER_BACKEND
    return value


def parse_odpm_ide(raw: str | None) -> str:
    value = (raw or "").strip() or DEFAULT_ODPM_IDE
    if value not in ODPM_IDE_VALUES:
        _logger.warning(
            _("Unknown ODPM_IDE=%r, using %s"),
            raw,
            DEFAULT_ODPM_IDE,
        )
        return DEFAULT_ODPM_IDE
    return value


def parse_debugger_connect_host(raw: str | None) -> str:
    value = (raw or "").strip()
    return value or DEFAULT_DEBUGGER_CONNECT_HOST


def parse_debugger_suspend(raw: str | None) -> bool:
    value = (raw or "").strip().lower()
    if not value or value in {"0", "false", "no", "off", "n"}:
        return False
    if value in {"1", "true", "yes", "on", "y"}:
        return True
    _logger.warning(_("Unknown ODPM_DEBUGGER_SUSPEND=%r, using false"), raw)
    return False
