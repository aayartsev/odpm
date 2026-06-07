"""Backward-compatible shim for ``dev_project.compose.service_builder``."""

from dev_project.config.payload import write_runtime_config
from dev_project.compose.service_builder import ComposeServiceBuilder

__all__ = ["ComposeServiceBuilder", "write_runtime_config"]
