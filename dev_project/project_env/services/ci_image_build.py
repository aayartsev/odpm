"""CI image build orchestration over CiImageBuilder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..ci_image import CiImageBuilder
from ...bake_venv import VenvInstallSpec

if TYPE_CHECKING:
    from ..environment import CreateProjectEnvironment


class CiImageBuildService:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env
        self._builder = CiImageBuilder(env)

    @property
    def config(self):
        return self.env.config

    def prepare_ci_build_context(self) -> None:
        self._builder.prepare_ci_build_context()

    def generate_ci_dockerfile(self) -> str:
        return self._builder.generate_ci_dockerfile()

    def build_ci_image(self) -> None:
        self._builder.build_ci_image()

    def read_ci_dockerignore_template(self) -> str:
        return self._builder._read_ci_dockerignore_template()

    def build_ci_venv_install_spec(self) -> VenvInstallSpec:
        return self._builder._build_ci_venv_install_spec()
