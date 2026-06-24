"""Database drift preview for odpm plan warnings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..database.drift import (
    detect_database_drift_for_config,
    has_blocking_database_drift,
    meaningful_database_drifts,
)
from ..database.drift_format import format_database_drift_warning
from .l10n import plan_msg

if TYPE_CHECKING:
    from ..config import Config
    from ..host.context import HostProjectContext
    from ..host.ports import BootstrapHandle

MSG_DATABASE_DRIFT_BLOCKING = (
    "Blocking database configuration drift detected; resolve before starting containers."
)


def collect_database_drift_warnings(config: Config) -> tuple[str, ...]:
    _current, drifts = detect_database_drift_for_config(config)
    if not drifts:
        return ()
    warnings = [format_database_drift_warning(drift) for drift in drifts]
    meaningful = meaningful_database_drifts(drifts)
    if meaningful and has_blocking_database_drift(meaningful):
        warnings.append(plan_msg(MSG_DATABASE_DRIFT_BLOCKING))
    return tuple(warnings)


def collect_database_drift_warnings_for_host(
    host_ctx: HostProjectContext,
    bootstrap: BootstrapHandle,
) -> tuple[str, ...]:
    """Plan warnings keyed by host project dir; drift uses bootstrap handle."""
    _ = host_ctx.project_dir
    return collect_database_drift_warnings(bootstrap.config)
