"""Compose plan-preview surface bound to :class:`~dev_project.host.ports.BootstrapHandle`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..host.ports import BootstrapHandle

if TYPE_CHECKING:
    from ..config import Config


@dataclass(frozen=True)
class ComposePreviewPort:
    """Read-only compose preview for prepare evaluate; uses bootstrap config only."""

    bootstrap: BootstrapHandle

    def runtime_cache_config(self) -> Config:
        return self.bootstrap.config

    def runtime_config_text(self) -> str | None:
        from ..plan.compose_preview import preview_runtime_config_text

        return preview_runtime_config_text(self.bootstrap.config)

    def compose_start_command_changed(self) -> bool:
        from ..plan.compose_preview import compose_start_command_changed

        return compose_start_command_changed(self.bootstrap.config)

    def preview_compose_service(self):
        from ..plan.compose_preview import preview_compose_service

        return preview_compose_service(self.bootstrap.config)
