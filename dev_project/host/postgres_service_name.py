"""Parse PostgreSQL Docker Compose service name from .env."""

from __future__ import annotations

import re

from .. import constants
from ..logging import get_module_logger

_logger = get_module_logger(__name__)

_VALID_POSTGRES_SERVICE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


def parse_postgres_service_name(raw: str | None) -> str:
    default = constants.DEFAULT_POSTGRES_SERVICE_NAME
    if raw is None:
        return default
    name = raw.strip()
    if not name:
        return default
    if not _VALID_POSTGRES_SERVICE_NAME.fullmatch(name):
        _logger.warning(
            "Invalid %s=%r (use lowercase letters, digits, '_' or '-'); using %s",
            constants.POSTGRES_SERVICE_NAME_ENV,
            raw,
            default,
        )
        return default
    return name
