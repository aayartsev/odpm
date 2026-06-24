"""Merge compose ``services`` / ``service_patches`` from nested dependency manifests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from ..manifest.compose_policy import validate_manifest_compose_services
from ..dependency_resolver import NestedOdpmFragment

if TYPE_CHECKING:
    from ..config.config import Config


def _dict_services(value: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for name, spec in value.items():
        if isinstance(spec, dict):
            result[str(name)] = dict(spec)
    return result


def merge_nested_compose_fragments(
    fragments: list[NestedOdpmFragment],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Merge nested dependency compose fields (later fragments override earlier)."""
    from ..yaml import merge_service_patch_maps, merge_services

    nested_services: dict[str, dict[str, Any]] = {}
    nested_patches: dict[str, dict[str, Any]] = {}
    for fragment in fragments:
        if fragment.services:
            validate_manifest_compose_services(fragment.services)
            nested_services = merge_services(
                nested_services, _dict_services(fragment.services)
            )
        if fragment.service_patches:
            nested_patches = merge_service_patch_maps(
                nested_patches, _dict_services(fragment.service_patches)
            )
    return nested_services, nested_patches


def inherit_nested_compose_into_manifest(
    config: Config,
    fragments: list[NestedOdpmFragment],
) -> None:
    """Apply nested ``services`` / ``service_patches`` onto host ``manifest_view``.

    Host manifest values win over nested dependencies for the same service or patch name.
    """
    if not fragments:
        return
    nested_services, nested_patches = merge_nested_compose_fragments(fragments)
    if not nested_services and not nested_patches:
        return
    from ..yaml import merge_service_patch_maps, merge_services

    view = config.bootstrap.manifest_view
    host_services = _dict_services(view.services if view is not None else None)
    host_patches = _dict_services(
        view.service_patches if view is not None else None
    )
    merged_services = merge_services(nested_services, host_services)
    merged_patches = merge_service_patch_maps(nested_patches, host_patches)

    if view is None:
        from .. import constants
        from .reader import ManifestView

        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm=None,
            raw_normalized=deepcopy(config.bootstrap.raw_odpm_json),
            services=merged_services or None,
            service_patches=merged_patches or None,
            source_raw=deepcopy(config.bootstrap.raw_odpm_json),
        )
        return

    config.bootstrap.manifest_view = replace(
        view,
        services=merged_services or None,
        service_patches=merged_patches or None,
    )
