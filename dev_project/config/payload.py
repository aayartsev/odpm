from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from .. import constants
from .types import ConfigToJson

if TYPE_CHECKING:
    from .config import Config


def compute_venv_lock_hash(config: Config) -> str:
    config.config_dict["arch"] = constants.ARCH
    payload: dict[str, str] = {}
    for key in constants.VENV_LOCK_KEYS:
        if key == "requirements_txt":
            payload[key] = ",".join(sorted(config.requirements_txt))
        elif key == "venv_mode":
            payload[key] = config.policy.venv_mode
        else:
            payload[key] = str(config.config_dict.get(key, ""))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def config_to_json(config: Config) -> bytes:
    payload = ConfigToJson(
        docker_odoo_dir=config.docker_odoo_dir,
        odoo_config_data=config.odoo_config_data,
        docker_path_odoo_conf=config.docker_path_odoo_conf,
        arguments=vars(config.arguments),
        db_creation_data=config.db_creation_data,
        db_manager_password=config.db_manager_password,
        docker_venv_dir=config.docker_venv_dir,
        docker_project_dir=config.docker_project_dir,
        requirements_txt=config.requirements_txt,
        odoo_version=config.odoo_version,
        python_version=config.python_version,
        venv_lock_hash=compute_venv_lock_hash(config),
        platform_name=config.platform_name,
        arch=config.arch,
        sql_queries=config.sql_queries,
        modules_to_update=config.update_modules.split(","),
        docker_dirs_with_addons=config.docker_dirs_with_addons,
        odpm_scenario=config.user_env.odpm_scenario,
        venv_mode=config.policy.venv_mode,
    )
    return json.dumps(payload).encode("utf-8")
