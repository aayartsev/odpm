"""Compose service fragment collection, materialization, and YAML rendering."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..extensions.context import ExtensionHostContext

from .command_render import yaml_scalar

_COMPOSE_FRAGMENTS_GITIGNORE = "*\n!.gitignore\n"


def compose_fragments_dir(project_dir: str) -> str:
    from .. import constants

    return os.path.join(project_dir, constants.COMPOSE_FRAGMENTS_DIR_REL_PATH)


def compose_fragments_snapshot_path(project_dir: str) -> str:
    from .. import constants

    return os.path.join(project_dir, constants.COMPOSE_FRAGMENTS_SNAPSHOT_REL_PATH)


def ensure_compose_fragments_gitignore(project_dir: str) -> None:
    fragments_dir = compose_fragments_dir(project_dir)
    os.makedirs(fragments_dir, exist_ok=True)
    gitignore_path = os.path.join(fragments_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        Path(gitignore_path).write_text(_COMPOSE_FRAGMENTS_GITIGNORE, encoding="utf-8")
        return
    existing = Path(gitignore_path).read_text(encoding="utf-8")
    if existing.strip() != _COMPOSE_FRAGMENTS_GITIGNORE.strip():
        Path(gitignore_path).write_text(_COMPOSE_FRAGMENTS_GITIGNORE, encoding="utf-8")


def collect_compose_services(ext: ExtensionHostContext) -> dict[str, dict[str, Any]]:
    """Merge manifest ``services`` with registered compose fragment plugins."""
    from ..extensions.registry import iter_compose_fragments

    services: dict[str, dict[str, Any]] = {}
    manifest_services = ext.manifest_services
    if isinstance(manifest_services, dict):
        for name, spec in manifest_services.items():
            if isinstance(spec, dict):
                services[str(name)] = dict(spec)
    for _name, plugin in iter_compose_fragments():
        plugin_services = plugin.compose_services(ext)
        if not isinstance(plugin_services, dict):
            continue
        for service_name, spec in plugin_services.items():
            if isinstance(spec, dict):
                services[str(service_name)] = dict(spec)
    return services


def services_snapshot_text(services: dict[str, dict[str, Any]]) -> str:
    return json.dumps(services, indent=2, sort_keys=True) + "\n"


def compose_fragments_need_materialize(
    project_dir: str,
    services: dict[str, dict[str, Any]],
) -> bool:
    snapshot_path = compose_fragments_snapshot_path(project_dir)
    fragments_dir = Path(compose_fragments_dir(project_dir))
    has_artifacts = os.path.isfile(snapshot_path) or any(fragments_dir.glob("*.yml"))
    if not services and not has_artifacts:
        return False
    expected = services_snapshot_text(services)
    if not os.path.isfile(snapshot_path):
        return True
    try:
        on_disk = Path(snapshot_path).read_text(encoding="utf-8")
    except OSError:
        return True
    return on_disk != expected


def materialize_compose_fragments(
    project_dir: str,
    services: dict[str, dict[str, Any]],
) -> None:
    """Write generated fragment YAML files and services snapshot under ``.odpm/compose/fragments``."""
    ensure_compose_fragments_gitignore(project_dir)
    fragments_dir = compose_fragments_dir(project_dir)
    for existing in Path(fragments_dir).glob("*.yml"):
        if existing.name != ".gitignore":
            existing.unlink()
    for name, spec in sorted(services.items()):
        block = render_compose_services_block({name: spec})
        service_yaml = block.strip() + "\n"
        Path(fragments_dir, f"{name}.yml").write_text(service_yaml, encoding="utf-8")
    Path(compose_fragments_snapshot_path(project_dir)).write_text(
        services_snapshot_text(services),
        encoding="utf-8",
    )


def render_compose_services_block(services: dict[str, dict[str, Any]]) -> str:
    """Render extra ``services:`` entries (2-space service indent) for template injection."""
    if not services:
        return ""
    lines: list[str] = []
    for name, spec in sorted(services.items()):
        lines.append(f"  {name}:")
        lines.extend(_render_mapping(spec, indent=4))
    return "\n".join(lines) + "\n"


def _render_mapping(value: dict[str, Any], *, indent: int) -> list[str]:
    lines: list[str] = []
    for key, item in value.items():
        lines.extend(_render_key_value(str(key), item, indent=indent))
    return lines


def _render_key_value(key: str, value: Any, *, indent: int) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines = [f"{prefix}{key}:"]
        for child_key, child_value in value.items():
            lines.extend(_render_key_value(str(child_key), child_value, indent=indent + 2))
        return lines
    if isinstance(value, list):
        lines = [f"{prefix}{key}:"]
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}  -")
                for child_key, child_value in item.items():
                    lines.extend(
                        _render_key_value(str(child_key), child_value, indent=indent + 4)
                    )
            else:
                lines.append(f"{prefix}  - {_render_scalar(item)}")
        return lines
    return [f"{prefix}{key}: {_render_scalar(value)}"]


def _render_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return yaml_scalar(str(value))
