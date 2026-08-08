"""Resolve CI image builder name and push flag from CLI / env."""

from __future__ import annotations

import os
from typing import Literal, Mapping

from ... import constants
from ...errors import PipelineError
from ...translations import _

CiImageBuilderName = Literal["docker", "kaniko"]


def _truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes"}


def resolve_ci_image_builder(
    arguments=None,
    environ: Mapping[str, str] | None = None,
) -> CiImageBuilderName:
    env = environ if environ is not None else os.environ
    cli = getattr(arguments, "image_builder", None) if arguments is not None else None
    raw = (cli or env.get(constants.ODPM_CI_IMAGE_BUILDER_ENV, "") or "").strip().lower()
    if not raw:
        return constants.CI_IMAGE_BUILDER_DOCKER
    if raw not in constants.CI_IMAGE_BUILDERS:
        message = _(
            "Unknown CI image builder {BUILDER!r}; expected one of: {ALLOWED}"
        ).format(
            BUILDER=raw,
            ALLOWED=", ".join(constants.CI_IMAGE_BUILDERS),
        )
        raise PipelineError(message)
    return raw  # type: ignore[return-value]


def resolve_ci_image_push(
    arguments=None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    env = environ if environ is not None else os.environ
    if arguments is not None and getattr(arguments, "image_push", False):
        return True
    return _truthy_env(env.get(constants.ODPM_CI_IMAGE_PUSH_ENV))
