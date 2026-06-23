"""Patch generated docker-compose.yml for in-repo HTTP smoke (Mailpit fixture)."""

from __future__ import annotations

import re

_SERVICE_HEADER = re.compile(r"^  ([a-z0-9_-]+):\s*$")
_PORT_LIST_ITEM = re.compile(r"^    - ")


def patch_mailpit_service_ports(
    content: str,
    *,
    ui_port: int,
    smtp_port: int,
    service_name: str = "mailpit",
) -> str:
    """Map Mailpit UI/SMTP to free host ports for isolated ``compose up``."""
    lines = content.splitlines(keepends=True)
    result: list[str] = []
    current_service: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        service_match = _SERVICE_HEADER.match(line)
        if service_match and not line.startswith("    "):
            current_service = service_match.group(1)
        if line.strip() == "ports:" and current_service == service_name:
            result.append("    ports:\n")
            result.append(f"    - {ui_port}:8025\n")
            result.append(f"    - {smtp_port}:1025\n")
            index += 1
            while index < len(lines) and _PORT_LIST_ITEM.match(lines[index]):
                index += 1
            continue
        result.append(line)
        index += 1
    return "".join(result)
