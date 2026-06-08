"""Typed, versioned container runtime configuration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants
from ..inside_docker_app.exceptions import ConfigValidationError, ContainerError
from .schema import CONTAINER_CONFIG_SCHEMA_VERSION, validate_container_config_dict

if TYPE_CHECKING:
    from ..config.config import Config


def _normalize_legacy_container_config(raw: dict) -> dict:
    """Apply v0 defaults, then validate against the v1 contract."""
    data = dict(raw)

    schema_version = data.get("schema_version")
    if schema_version is None:
        schema_version = CONTAINER_CONFIG_SCHEMA_VERSION
    else:
        schema_version = int(schema_version)
    data["schema_version"] = schema_version

    if "run_mode" not in data:
        data["run_mode"] = constants.RUN_MODE_ODOO

    if not data.get("venv_mode"):
        if data.get("odpm_scenario") == constants.CI_SCENARIO:
            data["venv_mode"] = constants.VENV_MODE_BAKED
        else:
            data["venv_mode"] = constants.VENV_MODE_FRESH

    if not data.get("odpm_scenario"):
        data["odpm_scenario"] = constants.DEFAULT_ODPM_SCENARIO

    data.setdefault("odoo_config_data", {})
    data.setdefault("arguments", {})
    data.setdefault("requirements_txt", [])
    data.setdefault("sql_queries", [])
    data.setdefault("modules_to_update", [])
    data.setdefault("docker_dirs_with_addons", [])
    data.setdefault("platform_name", constants.PLATFORM_NAME)

    if data.get("db_manager_password") is None:
        data["db_manager_password"] = ""

    validate_container_config_dict(data)
    return data


@dataclass
class DbCreationConfig:
    db_lang: str
    db_country_code: str | bool | None
    create_demo: bool
    db_default_admin_login: str
    db_default_admin_password: str

    @classmethod
    def from_dict(cls, raw: dict | None) -> DbCreationConfig:
        if not isinstance(raw, dict):
            raise ConfigValidationError("db_creation_data must be an object")
        return cls(
            db_lang=str(raw.get("db_lang", constants.DEFAULT_DB_CREATION_DATA_DB_LANG)),
            db_country_code=raw.get(
                "db_country_code", constants.DEFAULT_DB_CREATION_DATA_DB_COUNTRY_CODE
            ),
            create_demo=bool(
                raw.get("create_demo", constants.DEFAULT_DB_CREATION_DATA_CREATE_DEMO)
            ),
            db_default_admin_login=str(
                raw.get(
                    "db_default_admin_login",
                    constants.DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_LOGIN,
                )
            ),
            db_default_admin_password=str(
                raw.get(
                    "db_default_admin_password",
                    constants.DEFAULT_DB_CREATION_DATA_DB_DEFAULT_ADMIN_PASSWORD,
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContainerConfig:
    schema_version: int
    docker_odoo_dir: str
    odoo_config_data: dict
    docker_path_odoo_conf: str
    arguments: dict
    db_creation_data: DbCreationConfig
    db_manager_password: str
    docker_venv_dir: str
    docker_project_dir: str
    requirements_txt: list[str]
    odoo_version: str
    python_version: str
    venv_lock_hash: str
    platform_name: str
    arch: str
    sql_queries: list
    modules_to_update: list
    docker_dirs_with_addons: list
    odpm_scenario: str
    venv_mode: str
    run_mode: str

    @classmethod
    def from_odpm_config(cls, config: Config) -> ContainerConfig:
        from ..config.payload import compute_venv_lock_hash

        run_mode = getattr(config, "container_run_mode", constants.RUN_MODE_ODOO)
        return cls(
            schema_version=CONTAINER_CONFIG_SCHEMA_VERSION,
            docker_odoo_dir=config.docker_odoo_dir,
            odoo_config_data=config.odoo_config_data,
            docker_path_odoo_conf=config.docker_path_odoo_conf,
            arguments=vars(config.arguments),
            db_creation_data=DbCreationConfig.from_dict(config.db_creation_data),
            db_manager_password=config.db_manager_password or "",
            docker_venv_dir=config.docker_venv_dir,
            docker_project_dir=config.docker_project_dir,
            requirements_txt=list(config.requirements_txt),
            odoo_version=str(config.odoo_version),
            python_version=str(config.python_version),
            venv_lock_hash=compute_venv_lock_hash(config),
            platform_name=config.platform_name,
            arch=config.arch,
            sql_queries=list(config.sql_queries),
            modules_to_update=config.update_modules.split(",")
            if config.update_modules
            else [],
            docker_dirs_with_addons=list(config.docker_dirs_with_addons),
            odpm_scenario=config.user_env.odpm_scenario,
            venv_mode=config.policy.venv_mode,
            run_mode=run_mode,
        )

    @classmethod
    def from_dict(cls, raw: dict) -> ContainerConfig:
        if not isinstance(raw, dict):
            raise ConfigValidationError("Container config must be a JSON object")

        data = _normalize_legacy_container_config(raw)

        return cls(
            schema_version=data["schema_version"],
            docker_odoo_dir=str(data["docker_odoo_dir"]),
            odoo_config_data=dict(data.get("odoo_config_data") or {}),
            docker_path_odoo_conf=str(data["docker_path_odoo_conf"]),
            arguments=dict(data.get("arguments") or {}),
            db_creation_data=DbCreationConfig.from_dict(data.get("db_creation_data")),
            db_manager_password=str(data.get("db_manager_password") or ""),
            docker_venv_dir=str(data["docker_venv_dir"]),
            docker_project_dir=str(data["docker_project_dir"]),
            requirements_txt=list(data.get("requirements_txt") or []),
            odoo_version=str(data["odoo_version"]),
            python_version=str(data["python_version"]),
            venv_lock_hash=str(data["venv_lock_hash"]),
            platform_name=str(data.get("platform_name") or constants.PLATFORM_NAME),
            arch=str(data["arch"]),
            sql_queries=list(data.get("sql_queries") or []),
            modules_to_update=list(data.get("modules_to_update") or []),
            docker_dirs_with_addons=list(data.get("docker_dirs_with_addons") or []),
            odpm_scenario=str(data["odpm_scenario"]),
            venv_mode=str(data["venv_mode"]),
            run_mode=str(data["run_mode"]),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["db_creation_data"] = self.db_creation_data.to_dict()
        return payload

    def to_json_bytes(self) -> bytes:
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, indent=4) + "\n"
        ).encode("utf-8")


def load_container_config_from_path(path: str) -> ContainerConfig:
    return ContainerConfig.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def load_container_config_from_env() -> ContainerConfig:
    config_path = os.environ.get(
        constants.ODPM_CONFIG_PATH_ENV,
        constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH,
    )
    if not os.path.isfile(config_path):
        raise ContainerError(
            "Missing container config file: "
            f"{config_path} (set {constants.ODPM_CONFIG_PATH_ENV} or mount runtime config)"
        )
    return load_container_config_from_path(config_path)
