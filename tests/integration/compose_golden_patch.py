"""Patch generated docker-compose.yml for isolated golden-path E2E runs."""

from __future__ import annotations

import re
import socket

_SERVICE_HEADER = re.compile(r"^  ([a-z0-9_-]+):\s*$")
_POSTGRES_IMAGE = re.compile(r"^\s+image:\s+postgres(?::|\s|$)")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def postgres_service_name_from_compose(content: str) -> str:
    """Return the Postgres service name from compose (e.g. ``db`` or ``db-dev``)."""
    names = postgres_service_names_from_compose(content)
    return names[0] if names else "db"


def postgres_service_names_from_compose(content: str) -> tuple[str, ...]:
    current_service: str | None = None
    postgres_services: list[str] = []
    for line in content.splitlines():
        service_match = _SERVICE_HEADER.match(line)
        if service_match and not line.startswith("    "):
            current_service = service_match.group(1)
        if current_service and _POSTGRES_IMAGE.match(line):
            postgres_services.append(current_service)
    return tuple(postgres_services)


def patch_compose_for_golden_path(content: str, odoo_host_port: int) -> str:
    """Drop Postgres host ports; map Odoo HTTP to a free host port only."""
    postgres_services = frozenset(postgres_service_names_from_compose(content))
    lines = content.splitlines(keepends=True)
    result: list[str] = []
    current_service: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        service_match = _SERVICE_HEADER.match(line)
        if service_match and not line.startswith("    "):
            current_service = service_match.group(1)
        if (
            line.strip() == "ports:"
            and current_service in postgres_services
        ):
            index += 1
            while index < len(lines) and lines[index].startswith("      -"):
                index += 1
            continue
        if (
            line.strip() == "ports:"
            and current_service == "odoo"
        ):
            result.append("    ports:\n")
            result.append(f"      - {odoo_host_port}:8069\n")
            index += 1
            while index < len(lines) and lines[index].startswith("      -"):
                index += 1
            continue
        result.append(line)
        index += 1
    return "".join(result)
