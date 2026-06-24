"""Build structured docker-compose documents for :class:`ComposeGenerator`."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants
from ..config.payload import runtime_config_path
from ..database.paths import database_dir_path, ensure_database_dir_gitignore
from ..debugger.constants import DEFAULT_DEBUGGER_CONNECT_HOST
from ..debugger.user_env import (
    resolve_debugger_backend_id,
    resolve_debugger_connect_host,
)
from ..yaml import merge_services, merge_services_with_patches

if TYPE_CHECKING:
    from ..project_env.environment import CreateProjectEnvironment


def _resolve_postgres_service_name(user_env) -> str:
    name = getattr(user_env, "postgres_service_name", None)
    if isinstance(name, str) and name:
        return name
    return constants.DEFAULT_POSTGRES_SERVICE_NAME


def _resolve_port(user_env, attr: str, default: int) -> int:
    value = getattr(user_env, attr, None)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def _config_str(config, attr: str, default: str) -> str:
    value = getattr(config, attr, None)
    if isinstance(value, str) and value:
        return value
    return default


def _compose_command(compose_service) -> list[str]:
    command = getattr(compose_service, "command", None)
    if not isinstance(command, list) or not command:
        return ["python3", "-m", constants.RUN_ODOO_ENTRYPOINT, "--"]
    return [item if isinstance(item, str) else str(item) for item in command]


def _compose_working_dir(compose_service) -> str:
    working_dir = getattr(compose_service, "working_dir", None)
    if isinstance(working_dir, str) and working_dir:
        return working_dir
    return "/home/odoo"


def build_compose_document(env: CreateProjectEnvironment) -> dict[str, Any]:
    """Assemble the full compose mapping (services + volumes)."""
    from ..extensions.context import ExtensionHostContext
    from .fragments import collect_compose_services, collect_service_patches

    config = env.config
    policy = env.host_ctx.policy
    user_env = env.user_env
    compose_service = config.compose_service
    if compose_service is None:
        raise ValueError(
            "config.compose_service is required; run ComposeServiceBuilder.build() first"
        )

    odoo_image = _config_str(config, policy.odoo_image_attr, "odoo:dev")
    compose_user = policy.runtime_unix_user()
    db_name = _resolve_postgres_service_name(user_env)

    postgres_port = _resolve_port(user_env, "postgres_port", constants.POSTGRES_DEFAULT_PORT)
    postgres_port_map = policy.build_postgres_port_map(
        f"{postgres_port}:{constants.POSTGRES_DOCKER_PORT}"
    )
    debugger_port = _resolve_port(user_env, "debugger_port", constants.DEBUGGER_DEFAULT_PORT)
    debugger_port_map = f"{debugger_port}:{constants.DEBUGGER_DOCKER_PORT}"
    debugger_backend = resolve_debugger_backend_id(user_env)
    debugger_connect_host = resolve_debugger_connect_host(user_env)

    postgres_service: dict[str, Any] = {
        "image": f"postgres:{_config_str(config, 'postgres_version', '16')}",
        "user": "root",
        "tty": True,
        "ports": [postgres_port_map],
        "environment": [
            f"POSTGRES_PASSWORD={constants.POSTGRES_ODOO_PASS}",
            f"POSTGRES_USER={constants.POSTGRES_ODOO_USER}",
            "POSTGRES_DB=postgres",
        ],
        "volumes": ["postgres-data:/var/lib/postgresql/data"],
    }

    odoo_environment = ["PYTHONUNBUFFERED=1"]
    if policy.is_developer():
        odoo_environment.append(
            f"{constants.PYTHONWARNINGS_ENV}={constants.PYTHONWARNINGS_DEV_DOCUTILS}"
        )
    if compose_service.include_runtime_config:
        odoo_environment.append(
            f"{constants.ODPM_CONFIG_PATH_ENV}={constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}"
        )
    if compose_service.include_runtime_secrets:
        odoo_environment.append(
            f"{constants.ODPM_SECRETS_PATH_ENV}={constants.ODPM_SECRETS_CONTAINER_PATH}"
        )

    odoo_ports = [
        f"{_resolve_port(user_env, 'odoo_port', constants.ODOO_DEFAULT_PORT)}:{constants.ODOO_DOCKER_PORT}",
        f"{_resolve_port(user_env, 'gevent_port', constants.GEVENT_DEFAULT_PORT)}:{constants.GEVENT_DOCKER_PORT}",
    ]
    if policy.should_publish_debugger_port(debugger_backend):
        odoo_ports.append(debugger_port_map)

    odoo_service: dict[str, Any] = {
        "image": odoo_image,
        "user": compose_user,
        "tty": True,
        "depends_on": [db_name],
        "working_dir": _compose_working_dir(compose_service),
        "environment": odoo_environment,
        "command": _compose_command(compose_service),
        "ports": odoo_ports,
    }

    odoo_volumes = _build_odoo_volume_mounts(env, compose_service)
    if odoo_volumes:
        odoo_service["volumes"] = odoo_volumes

    if policy.should_add_debugger_extra_hosts(debugger_backend):
        if debugger_connect_host.strip() == DEFAULT_DEBUGGER_CONNECT_HOST:
            odoo_service["extra_hosts"] = ["host.docker.internal:host-gateway"]

    ext = ExtensionHostContext.from_config(config)
    base_services = {db_name: postgres_service, "odoo": odoo_service}
    fragment_services = collect_compose_services(ext)
    service_patches = collect_service_patches(ext)
    services = merge_services_with_patches(
        merge_services(base_services, fragment_services),
        service_patches,
    )

    return {
        "services": services,
        "volumes": {
            "postgres-data": {
                "driver": "local",
                "driver_opts": {
                    "type": "none",
                    "o": "bind",
                    "device": _config_str(
                        config,
                        "postgres_data_local_storage",
                        "/tmp/postgres-data",
                    ),
                },
            },
        },
    }


def _build_odoo_volume_mounts(
    env: CreateProjectEnvironment, compose_service
) -> list[str]:
    mounts: list[str] = []
    if compose_service.include_runtime_config:
        local_runtime_config_path = runtime_config_path(env.host_ctx.project_dir)
        mounts.append(
            f"{local_runtime_config_path}:{constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH}:ro,Z"
        )
        ensure_database_dir_gitignore(env.host_ctx.project_dir)
        local_database_dir = database_dir_path(env.host_ctx.project_dir)
        mounts.append(
            f"{local_database_dir}:{constants.ODPM_DATABASE_CONTAINER_DIR}:Z"
        )
    if compose_service.include_runtime_secrets:
        local_runtime_secrets_path = os.path.join(
            env.host_ctx.project_dir, constants.ODPM_SECRETS_RUNTIME_REL_PATH
        )
        mounts.append(
            f"{local_runtime_secrets_path}:{constants.ODPM_SECRETS_CONTAINER_PATH}:ro,Z"
        )
    if env.host_ctx.policy.include_odoo_volumes:
        for mapped_volume in env.mapped_folders:
            mounts.append(f"{mapped_volume.local}:{mapped_volume.docker}:Z")
            if not os.path.exists(mapped_volume.local):
                Path(mapped_volume.local).mkdir(parents=True, exist_ok=True)
    return mounts
