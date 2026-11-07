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

    def prepare_ci_build_context(self) -> None:
        self._builder.prepare_ci_build_context()

    def generate_ci_dockerfile(self) -> str:
        return self._builder.generate_ci_dockerfile()

    def build_ci_image(self) -> None:
        """Build final CI image via layered stages (ADR-027)."""
        from ...image_layers import run_layered_build

        run_layered_build(self.env, self.env.bootstrap.config.arguments)

    def read_ci_dockerignore_template(self) -> str:
        return self._builder._read_ci_dockerignore_template()

    def build_ci_venv_install_spec(self) -> VenvInstallSpec:
        return self._builder._build_ci_venv_install_spec()
