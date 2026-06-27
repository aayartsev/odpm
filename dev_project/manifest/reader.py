"""Dual-read manifest loader: v1 flat | v2 nested → normalized flat view."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .. import constants
from .compat import assert_manager_supports_manifest, parse_manifest_version_info
from .schema import validate_manifest_v2
from .odoo_conf_policy import validate_manifest_odoo_conf

if TYPE_CHECKING:
    from ..config.transforms.env_substitution import EnvResolver
    from .scenario_overrides import ScenarioManifestSlice


def _resolve_odoo_conf_dict(
    odoo_conf: dict[str, Any] | None,
    *,
    env_resolver: EnvResolver | None,
) -> dict[str, Any] | None:
    if not isinstance(odoo_conf, dict):
        return None
    if env_resolver is not None:
        from ..config.transforms.env_substitution import expand_env_in_odoo_conf

        expanded = expand_env_in_odoo_conf(dict(odoo_conf), resolver=env_resolver)
        return dict(expanded) if isinstance(expanded, dict) else None
    return dict(odoo_conf)


def _resolve_manifest_odoo_conf(
    raw: dict[str, Any],
    *,
    env_resolver: EnvResolver | None,
) -> dict[str, Any] | None:
    return _resolve_odoo_conf_dict(raw.get("odoo_conf"), env_resolver=env_resolver)


@dataclass(frozen=True)
class ManifestView:
    """Normalized host manifest for bootstrap and extension hooks."""

    manifest_schema: int
    requires_odpm: str | None
    raw_normalized: dict[str, Any]
    hooks: dict[str, Any] | None = None
    services: dict[str, Any] | None = None
    service_patches: dict[str, Any] | None = None
    locks: dict[str, Any] | None = None
    extensions: dict[str, Any] | None = None
    developing_git: str | None = None
    odoo_conf: dict[str, Any] | None = None
    scenario_slice: ScenarioManifestSlice | None = None
    source_raw: dict[str, Any] = field(repr=False, default_factory=dict)


def _ref_from_git_link(git_link: str) -> str:
    parts = git_link.strip().split()
    if len(parts) >= 2:
        return parts[-1]
    return ""


def normalize_v2_to_flat(
    raw: dict[str, Any],
    *,
    requirements_txt: list[str] | None = None,
) -> dict[str, Any]:
    """Map nested manifest v2 fields to legacy flat keys for bootstrap."""
    platform = raw.get("platform") or {}
    distro = raw.get("distro") or {}
    git_link = str(platform.get("git") or constants.ODOO_GIT_LINK)
    odoo_version = raw.get("odoo_version")
    if odoo_version is None or odoo_version == "":
        branch = _ref_from_git_link(git_link)
        odoo_version = branch or 0.0
    flat: dict[str, Any] = {
        "manifest_schema": constants.MANIFEST_SCHEMA_V2,
        "requires_odpm": raw.get("requires_odpm"),
        "odoo_version": odoo_version,
        "python_version": raw.get("python"),
        "distro_name": distro.get("name"),
        "distro_version": str(distro.get("version", "")),
        "postgres_version": str(raw.get("postgres", "")),
        "dependencies": list(raw.get("dependencies") or []),
        "requirements_txt": list(
            requirements_txt
            if requirements_txt is not None
            else (raw.get("requirements") or [])
        ),
        "odoo_git_link": git_link,
        "odoo_build_date": platform.get(
            "build_date", constants.ODOO_DEFAULT_BUILD_DATE
        ),
        "platform_name": raw.get("platform_name", constants.PLATFORM_NAME),
        "arch": raw.get("arch", constants.ARCH),
        "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
    }
    return flat


def load_manifest(
    raw: dict[str, Any],
    *,
    env_resolver: EnvResolver | None = None,
    active_scenario: str | None = None,
) -> ManifestView:
    """Validate, detect schema, and return a normalized :class:`ManifestView`."""
    from .scenario_overrides import (
        resolve_effective_manifest_slice,
        slice_from_manifest_fields,
        validate_scenario_manifest,
    )

    if not isinstance(raw, dict):
        raise TypeError("manifest root must be a JSON object")

    scenario = active_scenario or constants.DEFAULT_ODPM_SCENARIO
    if scenario not in constants.ODPM_SCENARIO_VALUES:
        scenario = constants.DEFAULT_ODPM_SCENARIO

    assert_manager_supports_manifest(raw)
    info = parse_manifest_version_info(raw)
    validate_scenario_manifest(raw)

    if info.manifest_schema == constants.MANIFEST_SCHEMA_V2:
        validate_manifest_v2(raw)
        effective = resolve_effective_manifest_slice(raw, scenario)
        raw_normalized = normalize_v2_to_flat(
            raw,
            requirements_txt=list(effective.requirements or []),
        )
        developing = raw.get("developing") or {}
        developing_git = developing.get("git")
        developing_git = str(developing_git).strip() if developing_git else None
        hooks = raw.get("hooks")
        services = effective.services
        service_patches = effective.service_patches
        locks = raw.get("locks")
        extensions = raw.get("extensions")
        if env_resolver is not None:
            from ..config.transforms.env_substitution import (
                expand_env_in_compose_service_map,
            )

            services = expand_env_in_compose_service_map(
                dict(services) if isinstance(services, dict) else None,
                resolver=env_resolver,
                field_prefix="services",
            )
            service_patches = expand_env_in_compose_service_map(
                dict(service_patches) if isinstance(service_patches, dict) else None,
                resolver=env_resolver,
                field_prefix="service_patches",
            )
        odoo_conf = _resolve_odoo_conf_dict(
            effective.odoo_conf,
            env_resolver=env_resolver,
        )
        return ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm=info.requires_odpm,
            raw_normalized=raw_normalized,
            hooks=dict(hooks) if isinstance(hooks, dict) else None,
            services=services if isinstance(services, dict) else None,
            service_patches=(
                service_patches if isinstance(service_patches, dict) else None
            ),
            locks=dict(locks) if isinstance(locks, dict) else None,
            extensions=dict(extensions) if isinstance(extensions, dict) else None,
            developing_git=developing_git,
            odoo_conf=odoo_conf,
            scenario_slice=effective,
            source_raw=deepcopy(raw),
        )

    validate_manifest_odoo_conf(raw)
    effective_v1 = slice_from_manifest_fields(
        odoo_conf=raw.get("odoo_conf"),
        requirements=raw.get("requirements_txt"),
    )
    odoo_conf = _resolve_odoo_conf_dict(
        effective_v1.odoo_conf,
        env_resolver=env_resolver,
    )
    return ManifestView(
        manifest_schema=constants.MANIFEST_SCHEMA_V1,
        requires_odpm=None,
        raw_normalized=deepcopy(raw),
        odoo_conf=odoo_conf,
        scenario_slice=effective_v1,
        source_raw=deepcopy(raw),
    )
