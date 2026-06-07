"""Backward-compatible shim for ``dev_project.project_env.compose``."""

from pathlib import Path

from dev_project.compose.generator import ComposeGenerator
from dev_project.project_dir_manager import template_needs_upgrade

__all__ = ["ComposeGenerator", "Path", "template_needs_upgrade"]
