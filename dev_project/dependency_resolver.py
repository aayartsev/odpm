"""Single-pass resolution of project dependencies including OCA transitive deps."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from . import constants
from .errors import ConfigError
from .translations import _
from .logging import get_module_logger

if TYPE_CHECKING:
    from .config.transforms.env_substitution import EnvResolver

_logger = get_module_logger(__name__)


@dataclass(frozen=True)
class NestedOdpmFragment:
    dependencies: list[str]
    requirements_txt: list[str]
    odoo_version: str | float | None
    python_version: str | None
    source_path: str
    services: dict[str, Any] | None = None
    service_patches: dict[str, Any] | None = None


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def read_nested_odpm_fragment(
    project_path: str,
    *,
    resolver: EnvResolver | None = None,
) -> NestedOdpmFragment | None:
    """Read dependency discovery fields from odpm.json at a dependency repo root."""
    manifest_path = os.path.join(project_path, constants.PROJECT_CONFIG_FILE_NAME)
    if not os.path.exists(manifest_path):
        return None
    try:
        with open(manifest_path, encoding="utf-8") as manifest_file:
            raw = json.load(manifest_file)
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning(
            _('Failed to read nested {CONFIG_FILE_NAME} at {MANIFEST_PATH}: {ERROR}').format(
                CONFIG_FILE_NAME=constants.PROJECT_CONFIG_FILE_NAME,
                MANIFEST_PATH=manifest_path,
                ERROR=exc,
            )
        )
        return None
    if not isinstance(raw, dict):
        _logger.warning(
            _('Nested {CONFIG_FILE_NAME} at {MANIFEST_PATH} must be a JSON object').format(
                CONFIG_FILE_NAME=constants.PROJECT_CONFIG_FILE_NAME,
                MANIFEST_PATH=manifest_path,
            )
        )
        return None

    if resolver is not None:
        from .config.transforms.env_substitution import (
            ODPM_JSON_ENV_EXPAND_FIELDS,
            expand_env_in_json,
        )

        raw = expand_env_in_json(
            raw,
            resolver=resolver,
            allowed_fields=ODPM_JSON_ENV_EXPAND_FIELDS,
        )

    odoo_version = raw.get("odoo_version")
    if odoo_version is not None and not isinstance(odoo_version, (str, int, float)):
        odoo_version = None

    python_version = raw.get("python_version")
    if python_version is not None:
        python_version = str(python_version).strip() or None

    services: dict[str, Any] | None = None
    service_patches: dict[str, Any] | None = None
    try:
        from .manifest.reader import load_manifest

        view = load_manifest(raw)
        services = view.services
        service_patches = view.service_patches
    except (TypeError, ValueError, ConfigError):
        services = None
        service_patches = None

    fragment = NestedOdpmFragment(
        dependencies=_normalize_string_list(raw.get("dependencies")),
        requirements_txt=_normalize_string_list(raw.get("requirements_txt")),
        odoo_version=odoo_version,
        python_version=python_version,
        source_path=manifest_path,
        services=services,
        service_patches=service_patches,
    )
    if (
        not fragment.dependencies
        and not fragment.requirements_txt
        and fragment.odoo_version is None
        and fragment.python_version is None
        and not fragment.services
        and not fragment.service_patches
    ):
        return None
    return fragment


@dataclass(frozen=True)
class DependencyDiscovery:
    urls: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    nested_fragment: NestedOdpmFragment | None = None


@dataclass(frozen=True)
class DependencyResolutionResult:
    urls: list[str]
    transitive_requirements: list[str]
    nested_fragments: list[NestedOdpmFragment]


def _append_unique_strings(target: list[str], items: Iterable[str]) -> None:
    seen = set(target)
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        target.append(text)


def resolve_dependencies(
    seed_urls: Iterable[str],
    discover: Callable[[str], DependencyDiscovery],
    *,
    initial_extra_urls: Iterable[str] | None = None,
) -> DependencyResolutionResult:
    """
    Resolve full dependency list in one pass, collecting transitive requirements
    and nested odpm.json fragments along the way.

    seed_urls: dependencies from host odpm.json (stable order).
    initial_extra_urls: URLs discovered from developing project before iteration.
    discover: callback for a checked-out dependency; checkout is caller responsibility.
    """
    queue: list[str] = []
    queued: set[str] = set()
    ordered: list[str] = []
    processed: set[str] = set()
    transitive_requirements: list[str] = []
    nested_fragments: list[NestedOdpmFragment] = []
    seen_fragment_paths: set[str] = set()

    def enqueue(urls: Iterable[str]) -> None:
        for url in urls:
            normalized = (url or "").strip()
            if not normalized or normalized in queued:
                continue
            queued.add(normalized)
            queue.append(normalized)

    def record_discovery(discovery: DependencyDiscovery) -> None:
        _append_unique_strings(transitive_requirements, discovery.requirements)
        fragment = discovery.nested_fragment
        if fragment is not None and fragment.source_path not in seen_fragment_paths:
            seen_fragment_paths.add(fragment.source_path)
            nested_fragments.append(fragment)

    enqueue(seed_urls)
    if initial_extra_urls:
        enqueue(initial_extra_urls)

    while queue:
        dependency_string = queue.pop(0)
        if dependency_string in processed:
            continue
        processed.add(dependency_string)
        ordered.append(dependency_string)
        discovery = discover(dependency_string)
        record_discovery(discovery)
        enqueue(discovery.urls)

    return DependencyResolutionResult(
        urls=ordered,
        transitive_requirements=transitive_requirements,
        nested_fragments=nested_fragments,
    )


def resolve_dependency_urls(
    seed_urls: Iterable[str],
    get_oca_urls: Callable[[str], list[str]],
    *,
    initial_extra_urls: Iterable[str] | None = None,
) -> list[str]:
    """
    Resolve full dependency list in one pass.

    seed_urls: dependencies from odpm.json (stable order).
    initial_extra_urls: URLs discovered from developing project oca_dependencies.txt
        before dependency iteration (same as legacy append-before-loop behavior).
    get_oca_urls: callback for a checked-out dependency; returns new URLs from its
        oca_dependencies.txt (project checkout is caller responsibility).
    """

    def discover(url: str) -> DependencyDiscovery:
        return DependencyDiscovery(urls=get_oca_urls(url))

    return resolve_dependencies(
        seed_urls,
        discover,
        initial_extra_urls=initial_extra_urls,
    ).urls


def parse_oca_dependencies_line(line: str) -> str | None:
    """Parse one line from oca_dependencies.txt into a git URL."""
    oca_dep_string = line.strip()
    if not oca_dep_string:
        return None
    if "#" in oca_dep_string:
        return None
    if "github" not in oca_dep_string:
        oca_dep_string = f"https://github.com/OCA/{oca_dep_string}.git"
    return oca_dep_string


def read_oca_dependency_urls(project_path: str) -> list[str]:
    """Read dependency URLs from oca_dependencies.txt under project_path."""
    oca_dependencies_txt = os.path.join(project_path, "oca_dependencies.txt")
    if not os.path.exists(oca_dependencies_txt):
        return []
    urls: list[str] = []
    with open(oca_dependencies_txt) as oca_deps:
        for line in oca_deps.readlines():
            url = parse_oca_dependencies_line(line)
            if url:
                urls.append(url)
    return urls
