"""Shared helpers for ContainerConfig unit tests."""

from dev_project import constants
from dev_project.container_config import CONTAINER_CONFIG_SCHEMA_VERSION, ContainerConfig

_DEFAULT_DEBUGGER = {
    "backend": "debugpy_listen",
    "port": 5678,
    "connect_host": "host.docker.internal",
    "suspend_on_connect": False,
}

_MINIMAL_CONTAINER_CONFIG = {
    "schema_version": CONTAINER_CONFIG_SCHEMA_VERSION,
    "docker_odoo_dir": "/home/odoo/odoo",
    "odoo_config_data": {},
    "docker_path_odoo_conf": "/home/odoo/odoo.conf",
    "arguments": {},
    "db_creation_data": dict(constants.DEFAULT_DB_CREATION_DATA),
    "docker_venv_dir": "/home/odoo/.venv",
    "docker_project_dir": "/home/odoo",
    "requirements_txt": [],
    "odoo_version": "19.0",
    "python_version": "3.12",
    "venv_lock_hash": "abc",
    "platform_name": "odoo",
    "arch": "amd64",
    "sql_queries": [],
    "modules_to_update": [],
    "docker_dirs_with_addons": [],
    "odpm_scenario": constants.DEVELOPER_SCENARIO,
    "venv_mode": constants.VENV_MODE_FRESH,
    "run_mode": constants.RUN_MODE_ODOO,
    "db_manager_password": "",
}


def _apply_debugger_defaults(payload: dict) -> dict:
    scenario = payload.get("odpm_scenario")
    if "debugger" not in payload:
        if scenario == constants.SERVER_SCENARIO or scenario == constants.CI_SCENARIO:
            payload["debugger"] = None
        else:
            payload["debugger"] = dict(_DEFAULT_DEBUGGER)
    return payload


def minimal_container_config(**overrides) -> ContainerConfig:
    payload = dict(_MINIMAL_CONTAINER_CONFIG)
    payload.update(overrides)
    if payload.get("venv_mode") is None:
        payload.pop("venv_mode", None)
    _apply_debugger_defaults(payload)
    return ContainerConfig.from_dict(payload)


def minimal_container_config_dict(**overrides) -> dict:
    payload = dict(_MINIMAL_CONTAINER_CONFIG)
    payload.update(overrides)
    if payload.get("venv_mode") is None:
        payload.pop("venv_mode", None)
    return _apply_debugger_defaults(payload)
