"""Single-pass resolution of project dependencies including OCA transitive deps."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import constants
from .translations import _
from .logging import get_module_logger

if TYPE_CHECKING:
    from .config.transforms.env_substitution import EnvResolver

_logger = get_module_logger(__name__)


@dataclass(frozen=True)
class NestedOdpmFragment:
    dependencies: list[str]
    odoo_version: str | float | None
    python_version: str | None
    source_path: str


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


def _nested_python_version(raw: dict) -> str | None:
    """Read Python version from nested odpm.json (v2 ``python`` or legacy ``python_version``)."""
    for key in ("python", "python_version"):
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def read_nested_odpm_fragment(
    project_path: str,
    *,
    resolver: EnvResolver | None = None,
) -> NestedOdpmFragment | None:
    """Read git dependency discovery fields from odpm.json at a dependency repo root.

    Sources-only: dependencies URLs and version metadata for compatibility checks.
    Nested ``services`` / ``requirements_txt`` are ignored.
    """
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
        from .config.transforms.env_substitution import (  # noqa: PLC0415  # optional
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

    fragment = NestedOdpmFragment(
        dependencies=_normalize_string_list(raw.get("dependencies")),
        odoo_version=odoo_version,
        python_version=_nested_python_version(raw),
        source_path=manifest_path,
    )
    if (
        not fragment.dependencies
        and fragment.odoo_version is None
        and fragment.python_version is None
    ):
        return None
    return fragment


@dataclass(frozen=True)
class DependencyDiscovery:
    urls: list[str] = field(default_factory=list)
    nested_fragment: NestedOdpmFragment | None = None


@dataclass(frozen=True)
class DependencyResolutionResult:
    urls: list[str]
    nested_fragments: list[NestedOdpmFragment]


def resolve_dependencies(
    seed_urls: Iterable[str],
    discover: Callable[[str], DependencyDiscovery],
    *,
    initial_extra_urls: Iterable[str] | None = None,
) -> DependencyResolutionResult:
    """
    Resolve full dependency list in one pass, collecting nested odpm.json fragments.

    seed_urls: dependencies from host odpm.json (stable order).
    initial_extra_urls: URLs discovered from developing project before iteration.
    discover: callback for a checked-out dependency; checkout is caller responsibility.
    """
    queue: list[str] = []
    queued: set[str] = set()
    ordered: list[str] = []
    processed: set[str] = set()
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
        nested_fragments=nested_fragments,
    )


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
