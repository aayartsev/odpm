import configparser
import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Optional

from .. import constants
from ..container_config import ContainerConfig
from .exceptions import ConfigValidationError, VenvError
from ..logging import get_module_logger

_logger = get_module_logger(__name__)

def write_odoo_config_data_to_file(odoo_config_data: dict, file_path: str) -> None:
    odoo_conf = configparser.ConfigParser()
    for section in odoo_config_data:
        odoo_conf[section] = {}
        for key, value in odoo_config_data[section].items():
            odoo_conf[section][key] = value
    with open(file_path, "w") as odoo_config_file:
        odoo_conf.write(odoo_config_file)


def delete_files_in_directory(directory_path):
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            _logger.warning(f"Failed to delete {file_path}. Reason: {e}")
            raise VenvError(
                f"Failed to delete {file_path}: {e}"
            ) from e


_BUILD_DATE_RE = re.compile(r"^(\d{4})-?(\d{2})-?(\d{2})$")


def _default_build_date_label() -> str:
    return constants.ODOO_DEFAULT_BUILD_DATE.lower()


def is_actionable_build_date(build_date: Optional[str]) -> bool:
    if not build_date:
        return False
    normalized = build_date.strip().lower()
    return normalized not in ("", _default_build_date_label())


def parse_build_date(build_date: str) -> datetime:
    match = _BUILD_DATE_RE.match(build_date.strip())
    if not match:
        raise ValueError(
            f"Invalid odoo_build_date {build_date!r}: expected YYYYMMDD or YYYY-MM-DD"
        )
    year, month, day = match.groups()
    return datetime(int(year), int(month), int(day))


def commit_before_timestamp(build_date: str) -> str:
    """End of build_date calendar day → git rev-list --before next midnight."""
    parsed = parse_build_date(build_date)
    next_day = parsed + timedelta(days=1)
    return next_day.strftime("%Y-%m-%d 00:00:00")


def shallow_since_date(build_date: str) -> str:
    parsed = parse_build_date(build_date)
    shallow_days = constants.PLATFORM_BUILD_DATE_SHALLOW_SINCE_DAYS
    since = parsed - timedelta(days=shallow_days)
    return since.strftime("%Y-%m-%d")


def resolve_venv_mode(config: ContainerConfig) -> str:
    """Return venv_mode from container config."""
    venv_mode = config.venv_mode
    if venv_mode not in constants.VENV_MODE_VALUES:
        message = (
            f"Invalid venv_mode {venv_mode!r} in container config; "
            f"expected one of {', '.join(sorted(constants.VENV_MODE_VALUES))}"
        )
        _logger.error(message)
        raise ConfigValidationError(message)
    return venv_mode


def resolve_venv_is_baked(config: ContainerConfig) -> bool:
    """True when virtualenv was pre-installed in the image (CI bake)."""
    return resolve_venv_mode(config) == constants.VENV_MODE_BAKED
