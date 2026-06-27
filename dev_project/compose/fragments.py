"""Compose service fragment collection, materialization, and YAML rendering."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants
from ..manifest.compose_policy import (
    reject_reserved_compose_service_name,
    validate_manifest_compose_services,
)

if TYPE_CHECKING:
    from ..extensions.context import ExtensionHostContext

_COMPOSE_FRAGMENTS_GITIGNORE = "*\n!.gitignore\n"


def collect_service_patches(ext: ExtensionHostContext) -> dict[str, dict[str, Any]]:
    """Return manifest and plugin ``service_patches`` for built-in compose services."""
    from ..extensions.registry import iter_compose_fragments
    from ..yaml import merge_service_patch_maps

    patches = ext.manifest_service_patches
    result: dict[str, dict[str, Any]] = {}
    if isinstance(patches, dict):
        for name, spec in patches.items():
            if isinstance(spec, dict):
                result[str(name)] = dict(spec)
    for _name, plugin in iter_compose_fragments():
        plugin_patches = getattr(plugin, "compose_service_patches", None)
        if plugin_patches is None:
            continue
        if callable(plugin_patches):
            plugin_patches = plugin_patches(ext)
        if not isinstance(plugin_patches, dict):
            continue
        normalized = {
            str(name): dict(spec)
            for name, spec in plugin_patches.items()
            if isinstance(spec, dict)
        }
        if normalized:
            result = merge_service_patch_maps(result, normalized)
    return result


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
        validate_manifest_compose_services(manifest_services)
        for name, spec in manifest_services.items():
            if isinstance(spec, dict):
                services[str(name)] = dict(spec)
    for _name, plugin in iter_compose_fragments():
        plugin_services = plugin.compose_services(ext)
        if not isinstance(plugin_services, dict):
            continue
        for service_name, spec in plugin_services.items():
            reject_reserved_compose_service_name(str(service_name), source="compose fragment plugin")
            if isinstance(spec, dict):
                services[str(service_name)] = dict(spec)
    return services


def _resolve_odpm_scenario(odpm_scenario: str | None) -> str:
    if isinstance(odpm_scenario, str) and odpm_scenario in constants.ODPM_SCENARIO_VALUES:
        return odpm_scenario
    return constants.DEFAULT_ODPM_SCENARIO


def services_snapshot_text(
    services: dict[str, dict[str, Any]],
    *,
    odpm_scenario: str | None = None,
) -> str:
    scenario = _resolve_odpm_scenario(odpm_scenario)
    payload = {"odpm_scenario": scenario, "services": services}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_services_snapshot_text(text: str) -> tuple[str | None, dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None, {}
    if not isinstance(payload, dict):
        return None, {}
    if "odpm_scenario" in payload and isinstance(payload.get("services"), dict):
        scenario = payload.get("odpm_scenario")
        return (
            str(scenario) if isinstance(scenario, str) else None,
            dict(payload["services"]),
        )
    if payload and all(isinstance(value, dict) for value in payload.values()):
        return None, dict(payload)
    return None, {}


def compose_fragments_need_materialize(
    project_dir: str,
    services: dict[str, dict[str, Any]],
    *,
    odpm_scenario: str | None = None,
) -> bool:
    snapshot_path = compose_fragments_snapshot_path(project_dir)
    fragments_dir = Path(compose_fragments_dir(project_dir))
    has_artifacts = os.path.isfile(snapshot_path) or any(fragments_dir.glob("*.yml"))
    if not services and not has_artifacts:
        return False
    scenario = _resolve_odpm_scenario(odpm_scenario)
    expected = services_snapshot_text(services, odpm_scenario=scenario)
    if not os.path.isfile(snapshot_path):
        return True
    try:
        on_disk = Path(snapshot_path).read_text(encoding="utf-8")
    except OSError:
        return True
    if on_disk == expected:
        return False
    on_disk_scenario, on_disk_services = _parse_services_snapshot_text(on_disk)
    if on_disk_scenario is None:
        return True
    if on_disk_scenario != scenario:
        return True
    return (
        json.dumps(on_disk_services, indent=2, sort_keys=True)
        != json.dumps(services, indent=2, sort_keys=True)
    )


def materialize_compose_fragments(
    project_dir: str,
    services: dict[str, dict[str, Any]],
    *,
    odpm_scenario: str | None = None,
) -> None:
    """Write generated fragment YAML files and services snapshot under ``.odpm/compose/fragments``."""
    from ..yaml import dump_document

    ensure_compose_fragments_gitignore(project_dir)
    fragments_dir = compose_fragments_dir(project_dir)
    for existing in Path(fragments_dir).glob("*.yml"):
        if existing.name != ".gitignore":
            existing.unlink()
    for name, spec in sorted(services.items()):
        service_yaml = dump_document({name: spec}).rstrip() + "\n"
        Path(fragments_dir, f"{name}.yml").write_text(service_yaml, encoding="utf-8")
    Path(compose_fragments_snapshot_path(project_dir)).write_text(
        services_snapshot_text(services, odpm_scenario=odpm_scenario),
        encoding="utf-8",
    )


def render_compose_services_block(services: dict[str, dict[str, Any]]) -> str:
    """Render extra ``services:`` entries (2-space service indent) for template injection."""
    if not services:
        return ""
    from ..yaml import dump_document

    lines: list[str] = []
    for name, spec in sorted(services.items()):
        for line in dump_document({name: spec}).splitlines():
            lines.append(f"  {line}")
    return "\n".join(lines) + "\n"
