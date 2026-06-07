"""Backward-compatible shim for ``dev_project.host.cli``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.host.cli")


from dev_project.host.cli import *  # noqa: F403
