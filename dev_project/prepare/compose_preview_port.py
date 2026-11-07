"""Compose plan-preview surface bound to :class:`~dev_project.host.ports.BootstrapHandle`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from ..host.ports import BootstrapHandle
from ..plan.compose_preview import (
    compose_preview_mutable_snapshot,
    compose_start_command_changed,
    preview_compose_service,
    preview_runtime_config_text,
    restore_compose_preview_mutable_snapshot,
)

_T = TypeVar("_T")


@dataclass(frozen=True)
class ComposePreviewPort:
    """Compose preview for prepare evaluate; AssembledProject stays behind the handle."""

    bootstrap: BootstrapHandle

    def run_with_mutable_snapshot(self, fn: Callable[[BootstrapHandle], _T]) -> _T:
        """Run *fn(bootstrap)* with compose preview mutable fields restored after."""
        bootstrap = self.bootstrap
        snapshot = compose_preview_mutable_snapshot(bootstrap)
        try:
            return fn(bootstrap)
        finally:
            restore_compose_preview_mutable_snapshot(bootstrap, snapshot)

    def runtime_config_text(self) -> str | None:
        return preview_runtime_config_text(self.bootstrap)

    def compose_start_command_changed(self) -> bool:
        return compose_start_command_changed(self.bootstrap)

    def preview_compose_service(self):
        return preview_compose_service(self.bootstrap)
