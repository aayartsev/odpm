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


def image_ref_exists(
    ref: str,
    *,
    remote: bool,
    force: bool = False,
) -> bool:
    """Return True if *ref* is already available.

    Remote registry refs require ``crane digest``. Local refs use
    ``docker image inspect``.

    ``force=True`` treats the ref as missing (current layer only). Callers
    must not pass force into nested parent-layer ensures.
    """
    if force:
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


def retag_image(source_ref: str, dest_ref: str, *, remote: bool) -> None:
    """Alias *source_ref* as *dest_ref* (local docker tag and/or crane copy)."""
    if source_ref == dest_ref:
        return
    if remote:
        crane = shutil.which("crane")
        if not crane:
            raise ConfigError(
                _(
                    "crane is required to retag remote layered CI images "
                    "({SRC} → {DST})"
                ).format(SRC=source_ref, DST=dest_ref)
            )
        completed = subprocess.run(
            [crane, "copy", source_ref, dest_ref],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ConfigError(
                _("crane copy failed ({SRC} → {DST}): {ERR}").format(
                    SRC=source_ref,
                    DST=dest_ref,
                    ERR=(completed.stderr or completed.stdout or "").strip(),
                )
            )
        _logger.info("retagged remote image %s → %s", source_ref, dest_ref)
        return
    docker = shutil.which("docker")
    if not docker:
        raise ConfigError(
            _("docker is required to retag local layered CI images")
        )
    completed = subprocess.run(
        [docker, "tag", source_ref, dest_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ConfigError(
            _("docker tag failed ({SRC} → {DST}): {ERR}").format(
                SRC=source_ref,
                DST=dest_ref,
                ERR=(completed.stderr or completed.stdout or "").strip(),
            )
        )
    _logger.info("retagged local image %s → %s", source_ref, dest_ref)
