"""Frozen host views for extension plugins (no mutable Config)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..host.context import HostProjectContext

if TYPE_CHECKING:
    from ..config import Config
    from ..manifest.reader import ManifestView


@dataclass(frozen=True)
class ExtensionHostContext:
    """Read-only host + manifest slice for plugins."""

    host: HostProjectContext
    repo_odpm_json: str
    manifest_schema: int | None = None
    requires_odpm: str | None = None
    manifest_services: dict[str, Any] | None = None
    manifest_service_patches: dict[str, Any] | None = None
    manifest_hooks: dict[str, Any] | None = None
    manifest_locks: dict[str, Any] | None = None
    manifest_extensions: dict[str, Any] | None = None

    @classmethod
    def from_config(cls, config: Config) -> ExtensionHostContext:
        host = HostProjectContext.from_config(config)
        return cls.from_host(
            host,
            repo_odpm_json=host.repo_odpm_json,
            manifest_view=host.manifest_view,
        )

    @classmethod
    def from_host(
        cls,
        host: HostProjectContext,
        *,
        repo_odpm_json: str,
        manifest_view: ManifestView | None,
    ) -> ExtensionHostContext:
        view = manifest_view
        return cls(
            host=host,
            repo_odpm_json=repo_odpm_json,
            manifest_schema=view.manifest_schema if view is not None else None,
            requires_odpm=view.requires_odpm if view is not None else None,
            manifest_services=view.services if view is not None else None,
            manifest_service_patches=(
                view.service_patches if view is not None else None
            ),
            manifest_hooks=view.hooks if view is not None else None,
            manifest_locks=view.locks if view is not None else None,
            manifest_extensions=view.extensions if view is not None else None,
        )

    @property
    def project_dir(self) -> str:
        return self.host.project_dir

    @property
    def policy(self):
        return self.host.policy
