from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
import hashlib
import json

from .. import constants
from ..container_config import ContainerConfig

if TYPE_CHECKING:
    from .config import AssembledProject


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


def config_to_json(config: AssembledProject) -> bytes:
    return ContainerConfig.from_odpm_config(config).to_json_bytes()


def write_runtime_config_to_path(config: AssembledProject, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_bytes(config_to_json(config))
    return path


def write_runtime_config(config: AssembledProject) -> str:
    path = runtime_config_path(config.project_dir)
    ensure_runtime_dir_gitignore(config.project_dir)
    return write_runtime_config_to_path(config, path)


def compute_extras_stamp(requirements_txt: list[str]) -> str:
    cleaned = sorted(req.strip() for req in requirements_txt if req and req.strip())
    canonical = json.dumps(cleaned, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_requirements_bytes(data: bytes) -> str:
    """SHA-256 of requirements.txt contents."""
    return hashlib.sha256(data).hexdigest()


def compute_odoo_requirements_hash(odoo_dir: str) -> str:
    """SHA-256 of ``{odoo_dir}/requirements.txt`` (empty when missing)."""
    if not odoo_dir or not isinstance(odoo_dir, str):
        return ""
    requirements_path = os.path.join(odoo_dir, "requirements.txt")
    if not os.path.isfile(requirements_path):
        return ""
    return hash_requirements_bytes(Path(requirements_path).read_bytes())


def resolve_odoo_requirements_hash(config: AssembledProject) -> str:
    """Override, host tree, then docker path (layout or flat attr)."""
    override = getattr(config, "odoo_requirements_hash_override", None)
    if isinstance(override, str) and override:
        return override
    host_dir = getattr(config, "odoo_src_dir", None)
    if isinstance(host_dir, str) and host_dir:
        hashed = compute_odoo_requirements_hash(host_dir)
        if hashed:
            return hashed
    docker_dir = ""
    layout = getattr(config, "docker_layout", None)
    if layout is not None:
        raw = getattr(layout, "docker_odoo_dir", None)
        if isinstance(raw, str):
            docker_dir = raw
    if not docker_dir:
        flat = getattr(config, "docker_odoo_dir", None)
        if isinstance(flat, str):
            docker_dir = flat
    return compute_odoo_requirements_hash(docker_dir)

def compute_venv_lock_hash(config: AssembledProject) -> str:

    arch = (
        config.project_settings.arch
        if config.project_settings.arch != "auto"
        else constants.ARCH
    )
    payload: dict[str, str] = {}
    for key in constants.VENV_LOCK_KEYS:
        if key == "venv_mode":
            payload[key] = config.policy.venv_mode
        elif key == "arch":
            payload[key] = str(arch)
        elif key == "python_version":
            payload[key] = str(config.project_settings.python_version)
        elif key == "distro_version":
            payload[key] = str(config.project_settings.distro_version)
        elif key == "distro_name":
            payload[key] = str(config.project_settings.distro_name)
        elif key == "postgres_version":
            payload[key] = str(config.project_settings.postgres_version)
        elif key == "odoo_version":
            payload[key] = str(config.project_settings.odoo_version)
        elif key == "odoo_requirements_hash":
            payload[key] = resolve_odoo_requirements_hash(config)
        else:
            payload[key] = ""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
