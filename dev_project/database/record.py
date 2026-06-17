"""Persist database last_run snapshots after successful PostgreSQL checks."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .. import constants
from .state import write_last_run_to_path

if TYPE_CHECKING:
    from ..container_config import ContainerConfig


def record_last_run_from_container(config: ContainerConfig) -> str | None:
    """Record last_run.json from checker after credentials succeed."""
    if config.database is None:
        return None
    snapshot = config.database.to_last_run(
        config.odpm_scenario,
        app_role_present=True,
    )
    os.makedirs(os.path.dirname(constants.ODPM_DATABASE_LAST_RUN_CONTAINER_PATH), exist_ok=True)
    return write_last_run_to_path(
        constants.ODPM_DATABASE_LAST_RUN_CONTAINER_PATH,
        snapshot,
    )
