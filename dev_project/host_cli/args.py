"""Backward-compatible shim for ``dev_project.host.cli.args``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.host.cli.args")


from dev_project.host.cli.args import *  # noqa: F403
