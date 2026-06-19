"""Host manifest schema detection, validation, and dual-read loader (4.4+)."""

from .compat import (
    ManifestVersionInfo,
    assert_manager_supports_manifest,
    parse_manifest_version_info,
)
from .reader import ManifestView, load_manifest, normalize_v2_to_flat
from .schema import manifest_schema_v1, manifest_schema_v2, validate_manifest_v2

__all__ = [
    "ManifestVersionInfo",
    "ManifestView",
    "assert_manager_supports_manifest",
    "load_manifest",
    "manifest_schema_v1",
    "manifest_schema_v2",
    "normalize_v2_to_flat",
    "parse_manifest_version_info",
    "validate_manifest_v2",
]
