"""Backward-compatible shim for ``dev_project.compose.service_builder``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.compose.service_builder")


from dev_project.config.payload import write_runtime_config
from dev_project.compose.service_builder import ComposeServiceBuilder

__all__ = ["ComposeServiceBuilder", "write_runtime_config"]
