"""Dual-read manifest loader: v1 flat | v2 nested → normalized flat view."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .. import constants
from .compat import assert_manager_supports_manifest, parse_manifest_version_info
from .schema import validate_manifest_v2
from ..compose.fragments import validate_manifest_compose_services


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
    source_raw: dict[str, Any] = field(repr=False, default_factory=dict)


def _ref_from_git_link(git_link: str) -> str:
    parts = git_link.strip().split()
    if len(parts) >= 2:
        return parts[-1]
    return ""


def normalize_v2_to_flat(raw: dict[str, Any]) -> dict[str, Any]:
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
        "requirements_txt": list(raw.get("requirements") or []),
        "odoo_git_link": git_link,
        "odoo_build_date": platform.get(
            "build_date", constants.ODOO_DEFAULT_BUILD_DATE
        ),
        "platform_name": raw.get("platform_name", constants.PLATFORM_NAME),
        "arch": raw.get("arch", constants.ARCH),
        "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
    }
    return flat


def load_manifest(raw: dict[str, Any]) -> ManifestView:
    """Validate, detect schema, and return a normalized :class:`ManifestView`."""
    if not isinstance(raw, dict):
        raise TypeError("manifest root must be a JSON object")

    assert_manager_supports_manifest(raw)
    info = parse_manifest_version_info(raw)

    if info.manifest_schema == constants.MANIFEST_SCHEMA_V2:
        validate_manifest_v2(raw)
        raw_normalized = normalize_v2_to_flat(raw)
        developing = raw.get("developing") or {}
        developing_git = developing.get("git")
        developing_git = str(developing_git).strip() if developing_git else None
        hooks = raw.get("hooks")
        services = raw.get("services")
        service_patches = raw.get("service_patches")
        validate_manifest_compose_services(services)
        locks = raw.get("locks")
        extensions = raw.get("extensions")
        return ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm=info.requires_odpm,
            raw_normalized=raw_normalized,
            hooks=dict(hooks) if isinstance(hooks, dict) else None,
            services=dict(services) if isinstance(services, dict) else None,
            service_patches=(
                dict(service_patches) if isinstance(service_patches, dict) else None
            ),
            locks=dict(locks) if isinstance(locks, dict) else None,
            extensions=dict(extensions) if isinstance(extensions, dict) else None,
            developing_git=developing_git,
            source_raw=deepcopy(raw),
        )

    return ManifestView(
        manifest_schema=constants.MANIFEST_SCHEMA_V1,
        requires_odpm=None,
        raw_normalized=deepcopy(raw),
        source_raw=deepcopy(raw),
    )
