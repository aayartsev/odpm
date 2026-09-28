"""Protocol for CI image build executors."""

from __future__ import annotations

from typing import Protocol

from .spec import ImageBuildSpec


class ImageBuildBackend(Protocol):
    def build(self, spec: ImageBuildSpec) -> None: ...
