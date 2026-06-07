"""Backward-compatible shim for ``dev_project.host.user_env``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.host.user_env")


from dev_project.host.user_env import *  # noqa: F403
