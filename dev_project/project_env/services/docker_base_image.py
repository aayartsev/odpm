"""Base Odoo Docker image orchestration over BaseImageBuilder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base_image import BaseImageBuilder

if TYPE_CHECKING:
    from ..environment import CreateProjectEnvironment


class BaseImageService:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env
        self._builder = BaseImageBuilder(env)

    @property
    def config(self):
        return self.env.config

    def base_image_exists(self) -> bool:
        return self._builder.base_image_exists()

    def build_base_image(self) -> None:
        self._builder.build_base_image()

    def ensure_base_image(self) -> None:
        self._builder.ensure_base_image()
