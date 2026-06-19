"""Host manifest schema detection and manager compatibility (4.4+)."""

from .compat import (
    ManifestVersionInfo,
    assert_manager_supports_manifest,
    parse_manifest_version_info,
)

__all__ = [
    "ManifestVersionInfo",
    "assert_manager_supports_manifest",
    "parse_manifest_version_info",
]
