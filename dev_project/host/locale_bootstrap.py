"""Early host locale bootstrap from layered ``.env`` before full pipeline setup."""

from __future__ import annotations

import os
from configparser import ConfigParser
from pathlib import Path

from .. import constants
from ..translations import apply_locale_from_sources


def read_odpm_locale_from_env_file(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    parser = ConfigParser()
    with open(path, encoding="utf-8") as stream:
        parser.read_string("[env]\n" + stream.read())
    raw = parser["env"].get(constants.ODPM_LOCALE_ENV_KEY, "").strip()
    return raw or None


def read_odpm_locale_from_layered_dotenv(
    *, project_path: str, config_home_dir: str
) -> str | None:
    """Return ``ODPM_LOCALE`` from merged home + project ``.env`` (project wins)."""
    from .user_env_parse import load_layered_dotenv_dict

    merged = load_layered_dotenv_dict(
        project_path=project_path,
        config_home_dir=config_home_dir,
    )
    raw = merged.get(constants.ODPM_LOCALE_ENV_KEY, "").strip()
    return raw or None


def bootstrap_host_locale(start_dir: str) -> str | None:
    """Apply ``ODPM_LOCALE`` from layered ``.env`` when present; else leave locale unchanged."""
    config_home_dir = os.path.join(Path.home(), constants.CONFIG_DIR_IN_HOME_DIR)
    odpm_locale = read_odpm_locale_from_layered_dotenv(
        project_path=start_dir,
        config_home_dir=config_home_dir,
    )
    if odpm_locale is None:
        return None
    return apply_locale_from_sources(odpm_locale)
