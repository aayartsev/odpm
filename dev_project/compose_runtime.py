"""Backward-compatible shim for ``dev_project.compose.runtime``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.compose.runtime")


from dev_project.subprocess_runner import run_checked
from dev_project.compose.runtime import (
    COMPOSE_STACK_SERVICES,
    _running_container_id,
    compose_stack_is_healthy,
    container_is_running_and_healthy,
    should_force_recreate_compose,
)

__all__ = [
    "COMPOSE_STACK_SERVICES",
    "_running_container_id",
    "compose_stack_is_healthy",
    "container_is_running_and_healthy",
    "run_checked",
    "should_force_recreate_compose",
]
