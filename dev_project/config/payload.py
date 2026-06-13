from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
import hashlib
import json

from .. import constants
from ..container_config import ContainerConfig

if TYPE_CHECKING:
    from .config import Config


def runtime_config_path(project_dir: str) -> str:
    from .. import constants

    return os.path.join(project_dir, constants.ODPM_RUNTIME_CONFIG_REL_PATH)


def ensure_runtime_dir_gitignore(project_dir: str) -> None:
    from .. import constants

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


def config_to_json(config: Config) -> bytes:
    return ContainerConfig.from_odpm_config(config).to_json_bytes()


def write_runtime_config_to_path(config: Config, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_bytes(config_to_json(config))
    return path


def write_runtime_config(config: Config) -> str:
    path = runtime_config_path(config.project_dir)
    ensure_runtime_dir_gitignore(config.project_dir)
    return write_runtime_config_to_path(config, path)


def compute_extras_stamp(requirements_txt: list[str]) -> str:
    cleaned = sorted(req.strip() for req in requirements_txt if req and req.strip())
    canonical = json.dumps(cleaned, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_venv_lock_hash(config: Config) -> str:

    arch = config.arch if config.arch != "auto" else constants.ARCH
    payload: dict[str, str] = {}
    for key in constants.VENV_LOCK_KEYS:
        if key == "venv_mode":
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
