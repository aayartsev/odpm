"""Registry / local image presence checks (ADR-027)."""

from __future__ import annotations

import os
import shutil
import subprocess

from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _

_logger = get_module_logger(__name__)


def force_rebuild_requested() -> bool:
    return os.environ.get("ODPM_IMAGE_FORCE_REBUILD", "").strip() in {
        "1",
        "true",
        "True",
        "yes",
        "YES",
    }


def image_ref_exists(ref: str, *, remote: bool) -> bool:
    """Return True if *ref* is already available.

    Remote registry refs require ``crane digest``. Local refs use
    ``docker image inspect``.
    """
    if force_rebuild_requested():
        _logger.info(
            "ODPM_IMAGE_FORCE_REBUILD set; treating %s as miss",
            ref,
        )
        return False
    if remote:
        return _crane_digest_exists(ref)
    return _docker_image_exists(ref)


def _crane_digest_exists(ref: str) -> bool:
    crane = shutil.which("crane")
    if not crane:
        message = _(
            "crane is required to check remote image presence for layered "
            "CI ensure (install crane or build without registry push)."
        )
        raise ConfigError(message)
    try:
        completed = subprocess.run(
            [crane, "digest", ref],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ConfigError(
            _("failed to run crane digest: {ERR}").format(ERR=exc)
        ) from exc
    if completed.returncode == 0 and (completed.stdout or "").strip():
        return True
    return False


def _docker_image_exists(ref: str) -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    completed = subprocess.run(
        [docker, "image", "inspect", ref],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0
