"""PostgreSQL container/host data paths (layout changes in official images 18+)."""

from __future__ import annotations

import os
import re

# Official postgres Docker images:
# - <=17: VOLUME/PGDATA at /var/lib/postgresql/data
# - >=18: mount /var/lib/postgresql; PGDATA=/var/lib/postgresql/{major}/docker
POSTGRES_DOCKER_LAYOUT_MAJOR = 18

POSTGRES_CONTAINER_MOUNT_LEGACY = "/var/lib/postgresql/data"
POSTGRES_CONTAINER_MOUNT_V18 = "/var/lib/postgresql"

POSTGRES_LOCAL_STORAGE_REL_LEGACY = "data/postgresql/var/lib/postgresql/data"
POSTGRES_LOCAL_STORAGE_REL_V18 = "data/postgresql/var/lib/postgresql"


def parse_postgres_major(postgres_version: str | int | None) -> int:
    """Return PostgreSQL major from image tag / manifest value (e.g. ``18``, ``16.4``)."""
    if postgres_version is None:
        return 0
    raw = str(postgres_version).strip()
    if not raw:
        return 0
    match = re.match(r"^(\d+)", raw)
    if not match:
        return 0
    return int(match.group(1))


def uses_postgres_v18_docker_layout(postgres_version: str | int | None) -> bool:
    return parse_postgres_major(postgres_version) >= POSTGRES_DOCKER_LAYOUT_MAJOR


def postgres_container_mount_path(postgres_version: str | int | None) -> str:
    """Compose volume target path inside the postgres container."""
    if uses_postgres_v18_docker_layout(postgres_version):
        return POSTGRES_CONTAINER_MOUNT_V18
    return POSTGRES_CONTAINER_MOUNT_LEGACY


def postgres_pgdata_path(postgres_version: str | int | None) -> str:
    """``PGDATA`` / ``postgres -D`` path inside the container."""
    major = parse_postgres_major(postgres_version)
    if major >= POSTGRES_DOCKER_LAYOUT_MAJOR:
        return f"{POSTGRES_CONTAINER_MOUNT_V18}/{major}/docker"
    return POSTGRES_CONTAINER_MOUNT_LEGACY


def postgres_local_storage_relpath(postgres_version: str | int | None) -> str:
    """Project-relative host bind directory for the postgres volume."""
    if uses_postgres_v18_docker_layout(postgres_version):
        return POSTGRES_LOCAL_STORAGE_REL_V18
    return POSTGRES_LOCAL_STORAGE_REL_LEGACY


def postgres_cluster_dir_on_host(
    storage_path: str, postgres_version: str | int | None
) -> str:
    """Host directory that contains ``PG_VERSION`` after initdb."""
    major = parse_postgres_major(postgres_version)
    if major >= POSTGRES_DOCKER_LAYOUT_MAJOR:
        return os.path.join(storage_path, str(major), "docker")
    return storage_path
