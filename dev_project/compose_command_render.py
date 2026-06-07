"""Backward-compatible shim for ``dev_project.compose.command_render``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.compose.command_render")


from dev_project.compose.command_render import *  # noqa: F403
