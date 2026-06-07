"""Backward-compatible shim for ``dev_project.plan.cli``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.plan.cli")


from dev_project.plan.cli import is_plan_mode

__all__ = ["is_plan_mode"]
