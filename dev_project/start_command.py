"""Backward-compatible shim for ``dev_project.compose.start_command``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.compose.start_command")


from dev_project.compose.start_command import *  # noqa: F403
