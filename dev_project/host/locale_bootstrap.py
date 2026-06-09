"""Early host locale bootstrap from project ``.env`` before full pipeline setup."""

from __future__ import annotations

import os
from configparser import ConfigParser

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


def bootstrap_host_locale(start_dir: str) -> str | None:
    """Apply ``ODPM_LOCALE`` from project ``.env`` when present; else leave locale unchanged."""
    env_path = os.path.join(start_dir, constants.ENV_FILE_NAME)
    odpm_locale = read_odpm_locale_from_env_file(env_path)
    if odpm_locale is None:
        return None
    return apply_locale_from_sources(odpm_locale)
