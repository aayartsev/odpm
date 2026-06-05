import base64
import json

from .check_odoo import OdooChecker
from .check_virtualenv import VirtualenvChecker


def decode_config(config_base64: str) -> dict:
    return json.loads(base64.b64decode(config_base64).decode())


def prepare_venv(config: dict) -> None:
    VirtualenvChecker(config)


def run_container_bootstrap(config: dict) -> None:
    prepare_venv(config)
    OdooChecker(config)


def main() -> None:
    from .parse_args import args

    run_container_bootstrap(decode_config(args.config_base64_data))
