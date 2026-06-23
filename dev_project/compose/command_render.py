"""Render docker-compose exec-form command blocks as YAML."""

from __future__ import annotations

from ..yaml import dump_document

# YAML 1.1 treats these unquoted scalars as non-strings in command lists.
_YAML_NON_STRING_SCALARS = frozenset(
    {"true", "false", "yes", "no", "on", "off", "null", "~"}
)


def yaml_scalar(value: str) -> str:
    """Legacy scalar quoting helper; prefer structured ``dump_document`` for new code."""
    if value == "":
        return '""'
    if value.isdigit() or value.lower() in _YAML_NON_STRING_SCALARS:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if all(ch.isalnum() or ch in "./_:@-" for ch in value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _indent_block(text: str, *, indent: int) -> str:
    prefix = " " * indent
    lines = text.rstrip("\n").splitlines()
    return "\n".join(f"{prefix}{line}" for line in lines) + "\n"


def render_compose_command_block(argv: list[str], *, indent: int = 4) -> str:
    block = dump_document({"command": list(argv)})
    return _indent_block(block, indent=indent)


def render_odpm_config_path_env_line(
    env_name: str, config_path: str, *, indent: int = 6
) -> str:
    if not config_path:
        return ""
    line = dump_document({"environment": [f"{env_name}={config_path}"]})
    env_line = next(
        line for line in line.splitlines() if line.lstrip().startswith("- ")
    )
    prefix = " " * indent
    return f"{prefix}{env_line.lstrip()}\n"
