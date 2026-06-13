"""Container bootstrap library: venv checks and Odoo pre-start tasks."""

from __future__ import annotations

from ..container_config import ContainerConfig
from .odoo_checker import OdooChecker
from .check_virtualenv import VirtualenvChecker


def prepare_venv(config: ContainerConfig) -> None:
    VirtualenvChecker(config)


def run_container_bootstrap(config: ContainerConfig) -> None:
    prepare_venv(config)
    OdooChecker(config)
