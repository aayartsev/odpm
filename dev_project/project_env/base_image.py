from __future__ import annotations

from typing import TYPE_CHECKING

from .. import constants
from ..translations import _
from ..errors import PipelineError, SubprocessError
from ..logging import get_module_logger
from ..subprocess_runner import run_or_raise
from ..system_check_policy import environ_from_config
from .base_image_identity import (
    base_image_identity_matches,
    expected_base_image_identity,
    read_base_image_identity,
    write_base_image_identity,
)
from .image_build import (
    ImageBuildSpec,
    get_ci_image_build_backend,
    resolve_ci_image_builder,
)
from .image_build.resolve import resolve_base_image_registry

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment

_logger = get_module_logger(__name__)


def _identity_mismatch_reason(config, *, image_ref: str | None = None) -> str | None:
    stamp = read_base_image_identity(config.project_dir)
    expected = expected_base_image_identity(config, image_ref=image_ref)
    if stamp is None:
        return "missing identity stamp"
    if stamp.get("base_image_profile") != expected.get("base_image_profile"):
        return (
            f"base image profile changed "
            f"({stamp.get('base_image_profile')!r} -> {expected.get('base_image_profile')!r})"
        )
    if stamp.get("dockerfile_sha256") != expected.get("dockerfile_sha256"):
        return "dockerfile changed (sha256 mismatch)"
    if (
        stamp.get("user") != expected.get("user")
        or stamp.get("uid") != expected.get("uid")
        or stamp.get("gid") != expected.get("gid")
    ):
        return "runtime Unix identity changed"
    if image_ref and stamp.get("image_ref") not in (None, image_ref):
        return (
            f"base image registry ref changed "
            f"({stamp.get('image_ref')!r} -> {image_ref!r})"
        )
    return None


class BaseImageBuilder:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def _builder_environ(self) -> dict[str, str]:
        return environ_from_config(self.config)

    def _builder_name(self) -> str:
        return resolve_ci_image_builder(
            self.config.arguments, environ=self._builder_environ()
        )

    def resolve_base_image_ref(self) -> str:
        from ..config.paths import ConfigPaths

        environ = self._builder_environ()
        builder_name = self._builder_name()
        registry = resolve_base_image_registry(environ)
        if builder_name == constants.CI_IMAGE_BUILDER_KANIKO:
            if not registry:
                message = _(
                    "Kaniko base image build requires {ENV} "
                    "(registry prefix for a pullable base image)."
                ).format(ENV=constants.ODPM_BASE_IMAGE_REGISTRY_ENV)
                raise PipelineError(message)
            return ConfigPaths(self.config).resolve_base_image_ref(registry=registry)
        return ConfigPaths(self.config).resolve_base_image_ref(registry=None)

    def base_image_exists(self) -> bool:
        builder_name = self._builder_name()
        image_ref = self.resolve_base_image_ref()
        if builder_name == constants.CI_IMAGE_BUILDER_KANIKO:
            return base_image_identity_matches(self.config, image_ref=image_ref)
        try:
            run_or_raise(["docker", "image", "inspect", image_ref])
        except SubprocessError:
            return False
        return True

    def build_base_image(self) -> None:
        environ = self._builder_environ()
        builder_name = resolve_ci_image_builder(
            self.config.arguments, environ=environ
        )
        image_ref = self.resolve_base_image_ref()
        push = builder_name == constants.CI_IMAGE_BUILDER_KANIKO
        spec = ImageBuildSpec(
            context_dir=self.config.project_dir,
            dockerfile=self.config.dockerfile_path,
            tag=image_ref,
            platform=f"linux/{self.config.arch}",
            push=push,
            project_dir=self.config.project_dir,
        )
        get_ci_image_build_backend(builder_name).build(spec)

    def ensure_base_image(self) -> None:
        image_ref = self.resolve_base_image_ref()
        image_exists = self.base_image_exists()
        identity_matches = base_image_identity_matches(
            self.config, image_ref=image_ref
        )
        if image_exists and identity_matches:
            return
        if image_exists and not identity_matches:
            reason = _identity_mismatch_reason(self.config, image_ref=image_ref)
            if reason:
                _logger.info(
                    "Base image %s stale: %s; rebuilding",
                    image_ref,
                    reason,
                )
            elif read_base_image_identity(self.config.project_dir) is None:
                _logger.info(
                    "Base image %s has no identity stamp; rebuilding to record "
                    "runtime identity",
                    image_ref,
                )
            else:
                _logger.info(
                    "Base image %s was built for a different runtime identity; "
                    "rebuilding",
                    image_ref,
                )
        self.build_base_image()
        write_base_image_identity(
            self.config.project_dir,
            expected_base_image_identity(self.config, image_ref=image_ref),
        )
