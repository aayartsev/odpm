"""Backward-compatible shim for ``dev_project.compose.ComposeGenerator``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.compose.ComposeGenerator")


from pathlib import Path

from dev_project.compose.generator import ComposeGenerator
from dev_project.project_dir_manager import template_needs_upgrade

__all__ = ["ComposeGenerator", "Path", "template_needs_upgrade"]
