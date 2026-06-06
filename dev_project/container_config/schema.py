"""ContainerConfig v1 contract validation (stdlib only, no third-party deps)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .. import constants
from ..inside_docker_app.exceptions import ConfigValidationError

CONTAINER_CONFIG_SCHEMA_VERSION = 1

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "container_config.v1.json"

_ALLOWED_KEYS = frozenset(
    {
        "schema_version",
        "docker_odoo_dir",
        "odoo_config_data",
        "docker_path_odoo_conf",
        "arguments",
        "db_creation_data",
        "db_manager_password",
        "docker_venv_dir",
        "docker_project_dir",
        "requirements_txt",
        "odoo_version",
        "python_version",
        "venv_lock_hash",
        "platform_name",
        "arch",
        "sql_queries",
        "modules_to_update",
        "docker_dirs_with_addons",
        "odpm_scenario",
        "venv_mode",
        "run_mode",
    }
)

_NON_EMPTY_STRING_FIELDS = (
    "docker_odoo_dir",
    "docker_path_odoo_conf",
    "docker_venv_dir",
    "docker_project_dir",
    "odoo_version",
    "python_version",
    "venv_lock_hash",
    "platform_name",
    "arch",
    "odpm_scenario",
    "venv_mode",
    "run_mode",
)

_STRING_LIST_FIELDS = (
    "requirements_txt",
    "modules_to_update",
    "docker_dirs_with_addons",
)


@lru_cache(maxsize=1)
def container_config_schema_v1() -> dict:
    """Load the documented JSON Schema contract (reference spec, not used at runtime)."""
    with _SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


def _require_dict(data: dict, field_name: str) -> None:
    if not isinstance(data.get(field_name), dict):
        raise ConfigValidationError(f"{field_name} must be an object")


def _require_list(data: dict, field_name: str) -> None:
    if not isinstance(data.get(field_name), list):
        raise ConfigValidationError(f"{field_name} must be an array")


def _require_string_list(data: dict, field_name: str) -> None:
    _require_list(data, field_name)
    for index, item in enumerate(data[field_name]):
        if not isinstance(item, str):
            raise ConfigValidationError(f"{field_name}[{index}] must be a string")


def validate_container_config_dict(data: dict) -> None:
    """Validate a normalized ContainerConfig v1 payload."""
    if not isinstance(data, dict):
        raise ConfigValidationError("Container config must be a JSON object")

    unknown_keys = sorted(set(data) - _ALLOWED_KEYS)
    if unknown_keys:
        raise ConfigValidationError(
            f"Unknown container config fields: {', '.join(unknown_keys)}"
        )

    for field_name in sorted(_ALLOWED_KEYS - set(data)):
        raise ConfigValidationError(
            f"Missing required container config field: {field_name}"
        )

    schema_version = data["schema_version"]
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise ConfigValidationError("schema_version must be an integer")
    if schema_version != CONTAINER_CONFIG_SCHEMA_VERSION:
        raise ConfigValidationError(
            f"Unsupported container config schema_version {schema_version!r}; "
            f"expected {CONTAINER_CONFIG_SCHEMA_VERSION}"
        )

    for field_name in _NON_EMPTY_STRING_FIELDS:
        value = data[field_name]
        if not isinstance(value, str) or value == "":
            raise ConfigValidationError(
                f"Missing required container config field: {field_name}"
            )

    if not isinstance(data["db_manager_password"], str):
        raise ConfigValidationError("db_manager_password must be a string")

    for field_name in ("odoo_config_data", "arguments", "db_creation_data"):
        _require_dict(data, field_name)

    for field_name in _STRING_LIST_FIELDS:
        _require_string_list(data, field_name)

    _require_list(data, "sql_queries")

    if data["odpm_scenario"] not in constants.ODPM_SCENARIO_VALUES:
        raise ConfigValidationError(
            f"Invalid odpm_scenario: {data['odpm_scenario']!r}"
        )

    if data["venv_mode"] not in constants.VENV_MODE_VALUES:
        raise ConfigValidationError(f"Invalid venv_mode: {data['venv_mode']!r}")

    if data["run_mode"] not in constants.RUN_MODE_VALUES:
        raise ConfigValidationError(f"Invalid run_mode: {data['run_mode']!r}")
