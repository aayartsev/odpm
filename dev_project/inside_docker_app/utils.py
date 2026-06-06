import configparser
import os
import re
import shutil
import json
from datetime import datetime, timedelta
from urllib.request import urlopen
import zipfile
from typing import Optional

from .. import constants
from ..container_config import ContainerConfig
from .exceptions import ConfigValidationError, VenvError
from .logger import get_module_logger

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

def get_direct_link_to_download_from_yadisk(yadisk_url):
    response = urlopen(constants.YADISK_API_ENDPOINT.format(yadisk_url))
    response_body_in_bytes = response.read()
    response_data = json.loads(response_body_in_bytes.decode("utf-8"))
    link_to_download = response_data["href"]
    return link_to_download

def printProgressBar (iteration, total):
    prefix = ""
    suffix = ""
    decimals = 1
    length = 100
    fill = "█"
    printEnd = "\r"
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + "-" * (length - filledLength)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end = printEnd)

def download_file(link_to_download, filepath_to_save):
    with urlopen(link_to_download) as response:
        meta = response.info()
        total_size = dict(meta._headers)["Content-Length"]
        offset = 0
        CHUNK = 16 * 1024
        with open(filepath_to_save, 'wb') as f:
            while True:
                chunk = response.read(CHUNK)
                offset += len(chunk)
                printProgressBar(float(offset), float(total_size))
                if not chunk:
                    break
                f.write(chunk)
    print()

def un_zip_file_to_directory(destination_dir, zip_file, rename_first_part_of_path=""):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        entries = zip_ref.infolist()
        total_entries = entries
        full_size = sum([entry.file_size for entry in total_entries])
        offset = 0
        for entry in total_entries:
            new_filename = entry.filename
            if rename_first_part_of_path:
                filename_parts = entry.filename.split(os.sep)
                new_filename = os.sep.join(filename_parts[1:])
                new_filename = os.path.join(rename_first_part_of_path, new_filename)
            full_file_path = os.path.join(destination_dir, new_filename)
            if entry.is_dir():
                if not os.path.exists(full_file_path):
                    os.makedirs(full_file_path)
                continue
            with zip_ref.open(entry) as content_from_zip:
                with open(full_file_path, "wb") as file_to_write:
                    while True:
                        b = content_from_zip.read(4096)
                        offset += len(b)
                        printProgressBar(float(offset), full_size)
                        if not b:
                            break
                        file_to_write.write(b)
        print()

def get_free_space(path):
    KB = 1024
    MB = 1024 * KB
    GB = 1024 * MB
    return shutil.disk_usage(path).free / GB


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