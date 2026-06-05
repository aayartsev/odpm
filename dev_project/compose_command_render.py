"""Render docker-compose exec-form command blocks as YAML."""

from __future__ import annotations


def yaml_scalar(value: str) -> str:
    if value == "":
        return '""'
    if all(ch.isalnum() or ch in "./_:@-" for ch in value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_compose_command_block(argv: list[str], *, indent: int = 4) -> str:
    prefix = " " * indent
    item_prefix = prefix + "  "
    lines = [f"{prefix}command:"]
    for token in argv:
        lines.append(f"{item_prefix}- {yaml_scalar(token)}")
    return "\n".join(lines) + "\n"


def render_odpm_config_env_line(
    env_name: str, config_b64: str, *, indent: int = 6
) -> str:
    if not config_b64:
        return ""
    prefix = " " * indent
    return f"{prefix}- {env_name}={yaml_scalar(config_b64)}\n"
