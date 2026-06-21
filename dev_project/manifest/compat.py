"""Manifest schema detection and manager compatibility checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from packaging.version import InvalidVersion, Version
except ImportError:
    from pip._vendor.packaging.version import InvalidVersion, Version

from .. import constants
from ..errors import ConfigError
from ..translations import _


@dataclass(frozen=True)
class ManifestVersionInfo:
    manifest_schema: int
    v1_contract_line: str | None = None
    requires_odpm: str | None = None


def _parse_semver(value: str, *, field_label: str) -> Version:
    try:
        return Version(value.strip())
    except InvalidVersion as exc:
        message = _(
            "Invalid {FIELD} value {VALUE!r}; expected a semantic version "
            "(for example 4.4 or 4.4.0)."
        ).format(FIELD=field_label, VALUE=value)
        raise ConfigError(message) from exc


def parse_manifest_version_info(raw: dict[str, Any]) -> ManifestVersionInfo:
    """Detect manifest schema and version fields from raw ``odpm.json``."""
    if "manifest_schema" in raw:
        schema_raw = raw["manifest_schema"]
        try:
            schema = int(schema_raw)
        except (TypeError, ValueError) as exc:
            message = _(
                "Invalid manifest_schema value {VALUE!r}; expected an integer."
            ).format(VALUE=schema_raw)
            raise ConfigError(message) from exc
        requires = raw.get("requires_odpm")
        requires_odpm = None
        if requires is not None:
            requires_odpm = str(requires).strip() or None
        if schema == constants.MANIFEST_SCHEMA_V1:
            contract = str(
                raw.get("odpm_version", constants.DEFAULT_ODPM_VERSION)
            ).strip()
            return ManifestVersionInfo(
                manifest_schema=schema,
                v1_contract_line=contract,
                requires_odpm=requires_odpm,
            )
        return ManifestVersionInfo(
            manifest_schema=schema,
            requires_odpm=requires_odpm,
        )

    contract = str(
        raw.get("odpm_version", constants.DEFAULT_ODPM_VERSION)
    ).strip()
    return ManifestVersionInfo(
        manifest_schema=constants.MANIFEST_SCHEMA_V1,
        v1_contract_line=contract,
    )


def assert_manager_supports_manifest(
    raw: dict[str, Any],
    *,
    manager_version: str | None = None,
) -> ManifestVersionInfo:
    """Raise :class:`ConfigError` when the manager cannot read this manifest."""
    info = parse_manifest_version_info(raw)
    manager = _parse_semver(
        manager_version or constants.ODPM_VERSION,
        field_label="manager version",
    )

    if info.manifest_schema > constants.MANIFEST_SCHEMA_SUPPORTED_MAX:
        message = _(
            "Unsupported manifest_schema {SCHEMA}; this manager supports "
            "manifest_schema up to {MAX_SCHEMA}."
        ).format(
            SCHEMA=info.manifest_schema,
            MAX_SCHEMA=constants.MANIFEST_SCHEMA_SUPPORTED_MAX,
        )
        raise ConfigError(message)

    if info.manifest_schema == constants.MANIFEST_SCHEMA_V1:
        contract = info.v1_contract_line or constants.DEFAULT_ODPM_VERSION
        if contract not in constants.SUPPORTED_V1_MANIFEST_CONTRACT_LINES:
            message = _(
                "Unsupported odpm.json contract line {CONTRACT}; supported "
                "values are {SUPPORTED}."
            ).format(
                CONTRACT=contract,
                SUPPORTED=", ".join(
                    sorted(constants.SUPPORTED_V1_MANIFEST_CONTRACT_LINES)
                ),
            )
            raise ConfigError(message)
        return info

    if info.manifest_schema == constants.MANIFEST_SCHEMA_V2:
        if not info.requires_odpm:
            message = _(
                "manifest_schema 2 requires requires_odpm (minimum odpm "
                "manager version)."
            )
            raise ConfigError(message)
        required = _parse_semver(info.requires_odpm, field_label="requires_odpm")
        if manager < required:
            message = _(
                "Manifest requires odpm manager {REQUIRES} or newer; "
                "current manager is {ODPM_VERSION}."
            ).format(
                REQUIRES=info.requires_odpm,
                ODPM_VERSION=str(manager),
            )
            raise ConfigError(message)
        return info

    message = _("Unsupported manifest_schema {SCHEMA}.").format(
        SCHEMA=info.manifest_schema
    )
    raise ConfigError(message)
