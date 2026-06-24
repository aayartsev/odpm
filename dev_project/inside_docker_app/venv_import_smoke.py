"""Smoke-import critical Odoo venv packages after activation."""

from __future__ import annotations

import importlib

from .. import constants
from ..logging import get_module_logger
from .exceptions import VenvError

_logger = get_module_logger(__name__)


def verify_venv_import_smoke(*, raise_on_failure: bool = True) -> bool:
    """Return True when all ``VENV_IMPORT_SMOKE_MODULES`` import successfully."""
    missing: list[str] = []
    for module_name in constants.VENV_IMPORT_SMOKE_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    if not missing:
        return True
    message = (
        "Virtualenv is missing Python packages required by Odoo: "
        f"{', '.join(missing)}. Re-run odpm to rebuild the virtualenv "
        "or install them manually."
    )
    _logger.error(message)
    if raise_on_failure:
        raise VenvError(message)
    return False
