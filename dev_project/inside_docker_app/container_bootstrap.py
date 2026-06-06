import base64
import json
import sys

from ..container_config import ContainerConfig
from .check_odoo import OdooChecker
from .check_virtualenv import VirtualenvChecker
from .exceptions import ContainerError
from .parse_args import parse_args


def decode_config(config_base64: str) -> dict:
    return json.loads(base64.b64decode(config_base64).decode())


def prepare_venv(config: ContainerConfig) -> None:
    VirtualenvChecker(config)


def run_container_bootstrap(config: ContainerConfig) -> None:
    prepare_venv(config)
    OdooChecker(config)


def main() -> None:

    try:
        run_container_bootstrap(
            ContainerConfig.from_dict(decode_config(parse_args().config_base64_data))
        )
    except ContainerError as exc:
        sys.exit(exc.exit_code)


if __name__ == "__main__":
    main()
