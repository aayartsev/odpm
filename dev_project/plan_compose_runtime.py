"""Backward-compatible shim for ``dev_project.plan.compose_runtime``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.plan.compose_runtime")


from dev_project.compose.runtime import should_force_recreate_compose
from dev_project.plan.compose_runtime import (
    PLAN_NO_DOCKER_WARNING,
    compose_up_force_recreate_value,
    compose_up_would_run,
    evaluate_compose_up_plan,
    plan_probes_compose_stack,
)

__all__ = [
    "PLAN_NO_DOCKER_WARNING",
    "compose_up_force_recreate_value",
    "compose_up_would_run",
    "evaluate_compose_up_plan",
    "plan_probes_compose_stack",
    "should_force_recreate_compose",
]
