"""Host manifest schema detection, validation, and dual-read loader (4.4+)."""

from .compat import (
    ManifestVersionInfo,
    assert_manager_supports_manifest,
    parse_manifest_version_info,
)
from .database import (
    database_block_from_user_settings,
    database_creation_overrides_from_manifest,
    merge_db_creation_from_manifest,
)
from .locks import (
    LockSource,
    deps_lock_from_manifest_git_locks,
    developing_git_link_from_config,
    git_locks_map_from_deps_lock,
    lookup_git_lock_commit,
    manifest_locks_from_deps_lock,
    resolve_lock_source,
)
from .migrator import format_manifest_migration_diff, migrate_v1_flat_to_v2
from .reader import ManifestView, load_manifest, normalize_v2_to_flat
from .schema import manifest_schema_v1, manifest_schema_v2, validate_manifest_v2

__all__ = [
    "LockSource",
    "ManifestVersionInfo",
    "ManifestView",
    "assert_manager_supports_manifest",
    "database_block_from_user_settings",
    "database_creation_overrides_from_manifest",
    "deps_lock_from_manifest_git_locks",
    "developing_git_link_from_config",
    "format_manifest_migration_diff",
    "git_locks_map_from_deps_lock",
    "load_manifest",
    "lookup_git_lock_commit",
    "manifest_locks_from_deps_lock",
    "manifest_schema_v1",
    "manifest_schema_v2",
    "merge_db_creation_from_manifest",
    "migrate_v1_flat_to_v2",
    "normalize_v2_to_flat",
    "parse_manifest_version_info",
    "resolve_lock_source",
    "validate_manifest_v2",
]
