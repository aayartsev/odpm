"""Per-scenario manifest overlays: merge helpers and validate (4.7 PR1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import constants
from ..errors import ConfigError
from ..extensions.hooks import LIFECYCLE_PHASES
from ..translations import _
from ..yaml import merge_service_patch_maps, merge_services
from .compose_policy import (
    validate_manifest_compose_services,
    warn_manifest_compose_stack_network,
)
from .service_sources import validate_service_source_fields
from .odoo_conf import _normalize_odoo_conf_sections, merge_odoo_conf_sections
from .odoo_conf_policy import validate_manifest_odoo_conf
from .secrets_policy import ManifestSecretsSpec, merge_secrets_spec, secrets_spec_from_raw
from .service_sources import merge_service_sources, normalize_service_sources


@dataclass(frozen=True)
class ScenarioManifestSlice:
    """Effective manifest fields for one scenario (odoo_conf / compose / requirements / deps / hooks / secrets)."""

    odoo_conf: dict[str, Any] | None = None
    services: dict[str, Any] | None = None
    service_patches: dict[str, Any] | None = None
    service_sources: dict[str, str] | None = None
    requirements: list[str] | None = None
    dependencies: list[str] | None = None
    hooks: dict[str, Any] | None = None
    secrets: ManifestSecretsSpec | None = None


def manifest_uses_scenarios(raw: dict[str, Any]) -> bool:
    """True when the manifest root declares ``scenarios`` (multi-mode), even if empty."""
    return "scenarios" in raw


def _optional_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict) and value:
        return dict(value)
    return None


def _optional_str_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    items = [str(item).strip() for item in value if item is not None and str(item).strip()]
    return items or None


def slice_from_manifest_fields(
    *,
    odoo_conf: Any = None,
    services: Any = None,
    service_patches: Any = None,
    service_sources: Any = None,
    requirements: Any = None,
    dependencies: Any = None,
    hooks: Any = None,
    secrets: Any = None,
) -> ScenarioManifestSlice:
    return ScenarioManifestSlice(
        odoo_conf=_optional_dict(odoo_conf),
        services=_optional_dict(services),
        service_patches=_optional_dict(service_patches),
        service_sources=normalize_service_sources(service_sources),
        requirements=_optional_str_list(requirements),
        dependencies=_optional_str_list(dependencies),
        hooks=_optional_dict(hooks),
        secrets=secrets_spec_from_raw(secrets),
    )


def top_level_slice(raw: dict[str, Any]) -> ScenarioManifestSlice:
    """Extract overlay-eligible fields from the manifest root."""
    return slice_from_manifest_fields(
        odoo_conf=raw.get("odoo_conf"),
        services=raw.get("services"),
        service_patches=raw.get("service_patches"),
        service_sources=raw.get("service_sources"),
        requirements=raw.get("requirements"),
        dependencies=raw.get("dependencies"),
        hooks=raw.get("hooks"),
        secrets=raw.get("secrets"),
    )


def scenario_overlay_slice(overlay: dict[str, Any]) -> ScenarioManifestSlice:
    """Extract fields from ``scenarios.<name>``."""
    return slice_from_manifest_fields(
        odoo_conf=overlay.get("odoo_conf"),
        services=overlay.get("services"),
        service_patches=overlay.get("service_patches"),
        service_sources=overlay.get("service_sources"),
        requirements=overlay.get("requirements"),
        dependencies=overlay.get("dependencies"),
        hooks=overlay.get("hooks"),
        secrets=overlay.get("secrets"),
    )


def _odoo_conf_sections(odoo_conf: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    if not odoo_conf:
        return {}
    normalized = _normalize_odoo_conf_sections(odoo_conf)
    return normalized or {}


def _manifest_odoo_conf_from_sections(
    sections: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    if not sections:
        return None
    return {section: dict(values) for section, values in sections.items()}


def _merge_string_list(
    base: list[str] | None,
    overlay: list[str] | None,
) -> list[str] | None:
    merged: list[str] = []
    seen: set[str] = set()
    for source in (base or []), (overlay or []):
        for item in source:
            cleaned = str(item).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                merged.append(cleaned)
    return merged or None


def _merge_hooks(
    base: dict[str, Any] | None,
    overlay: dict[str, Any] | None,
) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    for phase in LIFECYCLE_PHASES:
        phase_entries: list[Any] = []
        for source in (base or {}), (overlay or {}):
            entries = source.get(phase)
            if isinstance(entries, list):
                phase_entries.extend(entries)
        if phase_entries:
            merged[phase] = phase_entries
    return merged or None


def merge_manifest_slice(
    base: ScenarioManifestSlice,
    overlay: ScenarioManifestSlice,
    *,
    base_secrets_raw: Any = None,
    overlay_secrets_raw: Any = None,
) -> ScenarioManifestSlice:
    """Merge base manifest fields with a scenario overlay."""
    merged_odoo = _manifest_odoo_conf_from_sections(
        merge_odoo_conf_sections(
            _odoo_conf_sections(base.odoo_conf),
            _odoo_conf_sections(overlay.odoo_conf) or None,
        )
    )

    merged_services: dict[str, Any] | None
    if base.services or overlay.services:
        merged_services = merge_services(
            dict(base.services or {}),
            dict(overlay.services or {}),
        )
    else:
        merged_services = None

    merged_patches: dict[str, Any] | None
    if base.service_patches or overlay.service_patches:
        merged_patches = merge_service_patch_maps(
            dict(base.service_patches or {}),
            dict(overlay.service_patches or {}),
        )
    else:
        merged_patches = None

    return ScenarioManifestSlice(
        odoo_conf=merged_odoo,
        services=merged_services,
        service_patches=merged_patches,
        service_sources=merge_service_sources(
            base.service_sources,
            overlay.service_sources,
        ),
        requirements=_merge_string_list(base.requirements, overlay.requirements),
        dependencies=_merge_string_list(base.dependencies, overlay.dependencies),
        hooks=_merge_hooks(base.hooks, overlay.hooks),
        secrets=merge_secrets_spec(base_secrets_raw, overlay_secrets_raw),
    )


def resolve_effective_manifest_slice(
    raw: dict[str, Any],
    active_scenario: str,
) -> ScenarioManifestSlice:
    """Compute the effective manifest slice for ``active_scenario``."""
    scenario = active_scenario or constants.DEFAULT_ODPM_SCENARIO
    if scenario not in constants.ODPM_SCENARIO_VALUES:
        scenario = constants.DEFAULT_ODPM_SCENARIO

    base = top_level_slice(raw)
    if not manifest_uses_scenarios(raw):
        return base

    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, dict):
        scenarios = {}

    overlay_raw = scenarios.get(scenario)
    if not isinstance(overlay_raw, dict):
        return base

    return merge_manifest_slice(
        base,
        scenario_overlay_slice(overlay_raw),
        base_secrets_raw=raw.get("secrets"),
        overlay_secrets_raw=overlay_raw.get("secrets"),
    )


def _validate_hooks_fragment(hooks: dict[str, Any] | None) -> None:
    if hooks is None:
        return
    from ..extensions.hooks import LIFECYCLE_PHASES, parse_hook_phase

    for phase in LIFECYCLE_PHASES:
        parse_hook_phase(hooks, phase)


def _validate_odoo_conf_fragment(odoo_conf: dict[str, Any] | None) -> None:
    if odoo_conf is None:
        return
    validate_manifest_odoo_conf({"odoo_conf": odoo_conf})


def _validate_services_fragment(
    services: dict[str, Any] | None,
    *,
    service_sources: dict[str, str] | None = None,
    compose_network_logical: str | None = None,
) -> None:
    if services is None:
        return
    validate_manifest_compose_services(services)
    validate_service_source_fields(services, service_sources=service_sources)
    warn_manifest_compose_stack_network(
        services,
        compose_network_logical=compose_network_logical,
    )


def _validate_effective_slice(
    effective: ScenarioManifestSlice,
    *,
    compose_network_logical: str | None = None,
) -> None:
    _validate_odoo_conf_fragment(effective.odoo_conf)
    _validate_hooks_fragment(effective.hooks)
    _validate_services_fragment(
        effective.services,
        service_sources=effective.service_sources,
        compose_network_logical=compose_network_logical,
    )


def _validate_declared_overlays(
    raw: dict[str, Any],
    *,
    compose_network_logical: str | None = None,
) -> None:
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, dict):
        return
    for overlay_raw in scenarios.values():
        if not isinstance(overlay_raw, dict):
            continue
        overlay = scenario_overlay_slice(overlay_raw)
        _validate_odoo_conf_fragment(overlay.odoo_conf)
        _validate_hooks_fragment(overlay.hooks)
        _validate_services_fragment(
            overlay.services,
            service_sources=overlay.service_sources,
            compose_network_logical=compose_network_logical,
        )


def validate_scenario_manifest(
    raw: dict[str, Any],
    *,
    compose_network_logical: str | None = None,
) -> None:
    """Validate scenario overlays and effective slices (v2 only; call after JSON Schema)."""
    if "scenarios" in raw and raw.get("manifest_schema") != constants.MANIFEST_SCHEMA_V2:
        raise ConfigError(
            _(
                "manifest v1 does not support scenarios; "
                'run "odpm manifest migrate --write" to upgrade to manifest v2.'
            )
        )

    if raw.get("manifest_schema") != constants.MANIFEST_SCHEMA_V2:
        return

    if not manifest_uses_scenarios(raw):
        _validate_odoo_conf_fragment(_optional_dict(raw.get("odoo_conf")))
        _validate_hooks_fragment(_optional_dict(raw.get("hooks")))
        _validate_services_fragment(
            _optional_dict(raw.get("services")),
            service_sources=normalize_service_sources(raw.get("service_sources")),
            compose_network_logical=compose_network_logical,
        )
        return

    _validate_odoo_conf_fragment(_optional_dict(raw.get("odoo_conf")))
    _validate_hooks_fragment(_optional_dict(raw.get("hooks")))
    _validate_services_fragment(
        _optional_dict(raw.get("services")),
        service_sources=normalize_service_sources(raw.get("service_sources")),
        compose_network_logical=compose_network_logical,
    )
    _validate_declared_overlays(
        raw,
        compose_network_logical=compose_network_logical,
    )

    for scenario in sorted(constants.ODPM_SCENARIO_VALUES):
        _validate_effective_slice(
            resolve_effective_manifest_slice(raw, scenario),
            compose_network_logical=compose_network_logical,
        )
