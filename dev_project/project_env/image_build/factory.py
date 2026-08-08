"""Factory for CI image build backends."""

from __future__ import annotations

from ... import constants
from ...errors import PipelineError
from ...translations import _
from .docker_backend import DockerImageBuildBackend
from .kaniko_backend import KanikoImageBuildBackend
from .protocol import ImageBuildBackend


def get_ci_image_build_backend(name: str) -> ImageBuildBackend:
    if name == constants.CI_IMAGE_BUILDER_DOCKER:
        return DockerImageBuildBackend()
    if name == constants.CI_IMAGE_BUILDER_KANIKO:
        return KanikoImageBuildBackend()
    message = _(
        "Unknown CI image builder {BUILDER!r}; expected one of: {ALLOWED}"
    ).format(
        BUILDER=name,
        ALLOWED=", ".join(constants.CI_IMAGE_BUILDERS),
    )
    raise PipelineError(message)
