"""Patch generated docker-compose.yml for isolated golden-path E2E runs."""

from __future__ import annotations

import re
import socket


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def patch_compose_for_golden_path(content: str, odoo_host_port: int) -> str:
    """Drop Postgres host ports; map Odoo HTTP to a free host port only."""
    lines = content.splitlines(keepends=True)
    result: list[str] = []
    current_service: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        service_match = re.match(r"^  ([a-z0-9_-]+):\s*$", line)
        if service_match and not line.startswith("    "):
            current_service = service_match.group(1)
        if (
            line.strip() == "ports:"
            and current_service == "db"
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
