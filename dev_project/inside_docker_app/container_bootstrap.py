"""Container bootstrap library: venv checks and Odoo pre-start tasks.

Compose and normal runtime use ``run_odoo`` (config file via ``ODPM_CONFIG_PATH``).
The ``main()`` entry here is a deprecated base64-only bootstrap CLI (no odoo exec).
"""

from __future__ import annotations

import base64
import json
import sys
import warnings

from ..container_config import ContainerConfig
from .check_odoo import OdooChecker
from .check_virtualenv import VirtualenvChecker
from .exceptions import ContainerError
from .logger import get_module_logger
from .parse_args import parse_args

_logger = get_module_logger(__name__)

_CONTAINER_BOOTSTRAP_MAIN_DEPRECATION = (
    "container_bootstrap.main() with --config-base64-data is deprecated; "
    "use python3 -m dev_project.inside_docker_app.run_odoo with ODPM_CONFIG_PATH, "
    "or call run_container_bootstrap() from library code"
)


def decode_config(config_base64: str) -> dict:
    return json.loads(base64.b64decode(config_base64).decode())


def prepare_venv(config: ContainerConfig) -> None:
    VirtualenvChecker(config)


def run_container_bootstrap(config: ContainerConfig) -> None:
    prepare_venv(config)
    OdooChecker(config)


def main() -> None:
    """Deprecated: decode base64 JSON config and run bootstrap only (no odoo exec)."""
    warnings.warn(_CONTAINER_BOOTSTRAP_MAIN_DEPRECATION, DeprecationWarning, stacklevel=2)
    _logger.warning(_CONTAINER_BOOTSTRAP_MAIN_DEPRECATION)

    try:
        run_container_bootstrap(
            ContainerConfig.from_dict(decode_config(parse_args().config_base64_data))
        )
    except ContainerError as exc:
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
