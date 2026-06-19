"""Host manifest schema detection, validation, and dual-read loader (4.4+)."""

from .compat import (
    ManifestVersionInfo,
    assert_manager_supports_manifest,
    parse_manifest_version_info,
)
from .database import (
    database_creation_overrides_from_manifest,
    merge_db_creation_from_manifest,
)
from .reader import ManifestView, load_manifest, normalize_v2_to_flat
from .schema import manifest_schema_v1, manifest_schema_v2, validate_manifest_v2

__all__ = [
    "ManifestVersionInfo",
    "ManifestView",
    "assert_manager_supports_manifest",
    "database_creation_overrides_from_manifest",
    "load_manifest",
    "manifest_schema_v1",
    "manifest_schema_v2",
    "merge_db_creation_from_manifest",
    "normalize_v2_to_flat",
    "parse_manifest_version_info",
    "validate_manifest_v2",
]
