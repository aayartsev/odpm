from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from .. import constants
from .types import ConfigToJson

if TYPE_CHECKING:
    from .config import Config


def compute_venv_lock_hash(config: Config) -> str:
    arch = config.arch if config.arch != "auto" else constants.ARCH
    payload: dict[str, str] = {}
    for key in constants.VENV_LOCK_KEYS:
        if key == "requirements_txt":
            payload[key] = ",".join(sorted(config.requirements_txt))
        elif key == "venv_mode":
            payload[key] = config.policy.venv_mode
        elif key == "arch":
            payload[key] = str(arch)
        elif key == "python_version":
            payload[key] = str(config.python_version)
        elif key == "distro_version":
            payload[key] = str(config.distro_version)
        elif key == "distro_name":
            payload[key] = str(config.distro_name)
        elif key == "postgres_version":
            payload[key] = str(config.postgres_version)
        elif key == "odoo_version":
            payload[key] = str(config.odoo_version)
        else:
            payload[key] = ""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def config_to_json(config: Config) -> bytes:
    run_mode = getattr(config, "container_run_mode", constants.RUN_MODE_ODOO)
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
        run_mode=run_mode,
    )
    return json.dumps(payload).encode("utf-8")


def runtime_config_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_RUNTIME_CONFIG_REL_PATH)


def ensure_runtime_dir_gitignore(project_dir: str) -> None:
    runtime_dir = os.path.join(project_dir, constants.ODPM_RUNTIME_DIR_REL_PATH)
    os.makedirs(runtime_dir, exist_ok=True)
    gitignore_path = os.path.join(runtime_dir, ".gitignore")
    content = "*\n!.gitignore\n"
    if not os.path.exists(gitignore_path):
        Path(gitignore_path).write_text(content, encoding="utf-8")
        return
    existing = Path(gitignore_path).read_text(encoding="utf-8")
    if existing.strip() != content.strip():
        Path(gitignore_path).write_text(content, encoding="utf-8")


def write_runtime_config(config: Config) -> str:
    path = runtime_config_path(config.project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ensure_runtime_dir_gitignore(config.project_dir)
    Path(path).write_bytes(config_to_json(config))
    return path
