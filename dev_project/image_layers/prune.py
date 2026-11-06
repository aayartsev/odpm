"""Prune stale layered CI cache tags (ADR-027 § prune)."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

from ..logging import get_module_logger

if TYPE_CHECKING:
    from ..host.cli.args import OdpmCliArgs

_logger = get_module_logger(__name__)

ODPM_IMAGE_PRUNE_STALE_ENV = "ODPM_IMAGE_PRUNE_STALE"

_TRUTHY = frozenset({"1", "true", "True", "yes", "YES"})
_CACHE_FP_MARKER = "-v-"


def prune_stale_requested(args: OdpmCliArgs | None = None) -> bool:
    """True when CLI ``--image-prune-stale`` or env requests prune."""
    if args is not None and bool(getattr(args, "image_prune_stale", False)):
        return True
    return os.environ.get(ODPM_IMAGE_PRUNE_STALE_ENV, "").strip() in _TRUTHY


def split_image_ref(ref: str) -> tuple[str, str]:
    """Split ``registry/repo:tag`` into ``(repo, tag)`` (last colon)."""
    if ":" not in ref:
        raise ValueError(f"image ref missing tag: {ref!r}")
    repo, tag = ref.rsplit(":", 1)
    if not repo or not tag:
        raise ValueError(f"invalid image ref: {ref!r}")
    return repo, tag


def parse_cache_tag(tag: str) -> tuple[str, str] | None:
    """Return ``(prefix_with_v-, fingerprint)`` for ``cache-…-v-<fp>`` tags."""
    if not tag.startswith("cache-") or _CACHE_FP_MARKER not in tag:
        return None
    idx = tag.rfind(_CACHE_FP_MARKER)
    prefix = tag[: idx + len(_CACHE_FP_MARKER)]
    fingerprint = tag[idx + len(_CACHE_FP_MARKER) :]
    if not fingerprint:
        return None
    return prefix, fingerprint


def select_stale_cache_tags(
    tags: list[str],
    *,
    keep_tag: str,
) -> list[str]:
    """Tags sharing keep's ``cache-…-v-`` prefix but not equal to *keep_tag*."""
    parsed = parse_cache_tag(keep_tag)
    if parsed is None:
        return []
    prefix, _keep_fp = parsed
    stale: list[str] = []
    for tag in tags:
        if tag == keep_tag:
            continue
        if not tag.startswith(prefix):
            continue
        if parse_cache_tag(tag) is None:
            continue
        stale.append(tag)
    return stale


def _crane_ls(repo: str) -> list[str] | None:
    crane = shutil.which("crane")
    if not crane:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: crane not found; skipping remote prune "
            "for %s",
            repo,
        )
        return None
    try:
        completed = subprocess.run(
            [crane, "ls", repo],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: crane ls failed for %s: %s", repo, exc
        )
        return None
    if completed.returncode != 0:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: crane ls failed for %s: %s",
            repo,
            (completed.stderr or completed.stdout or "").strip(),
        )
        return None
    return [
        line.strip()
        for line in (completed.stdout or "").splitlines()
        if line.strip()
    ]


def _crane_delete(ref: str) -> None:
    crane = shutil.which("crane")
    if not crane:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: crane not found; cannot delete %s", ref
        )
        return
    try:
        completed = subprocess.run(
            [crane, "delete", ref],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: crane delete %s failed: %s", ref, exc
        )
        return
    if completed.returncode != 0:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: crane delete %s failed: %s",
            ref,
            (completed.stderr or completed.stdout or "").strip(),
        )
        return
    _logger.info("pruned remote cache tag %s", ref)


def _docker_list_tags(repo: str) -> list[str]:
    docker = shutil.which("docker")
    if not docker:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: docker not found; skipping local prune "
            "for %s",
            repo,
        )
        return []
    try:
        completed = subprocess.run(
            [
                docker,
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                repo,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: docker images failed for %s: %s",
            repo,
            exc,
        )
        return []
    if completed.returncode != 0:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: docker images failed for %s: %s",
            repo,
            (completed.stderr or completed.stdout or "").strip(),
        )
        return []
    tags: list[str] = []
    prefix = f"{repo}:"
    for line in (completed.stdout or "").splitlines():
        ref = line.strip()
        if not ref.startswith(prefix):
            continue
        tag = ref[len(prefix) :]
        if tag and tag != "<none>":
            tags.append(tag)
    return tags


def _docker_rmi(ref: str) -> None:
    docker = shutil.which("docker")
    if not docker:
        return
    try:
        completed = subprocess.run(
            [docker, "rmi", ref],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: docker rmi %s failed: %s", ref, exc
        )
        return
    if completed.returncode != 0:
        # Missing local image is expected after kaniko-only builds.
        err = (completed.stderr or completed.stdout or "").strip()
        if "No such image" in err or "image is required" in err.lower():
            _logger.debug(
                "ODPM_IMAGE_PRUNE_STALE: local image absent %s", ref
            )
            return
        _logger.warning(
            "ODPM_IMAGE_PRUNE_STALE: docker rmi %s failed: %s", ref, err
        )
        return
    _logger.info("pruned local cache tag %s", ref)


def prune_stale_layer_cache_tags(keep_ref: str, *, remote: bool) -> None:
    """Delete stale ``cache-<layer>-…-v-*`` tags; keep *keep_ref*. Fail-soft."""
    try:
        repo, keep_tag = split_image_ref(keep_ref)
    except ValueError as exc:
        _logger.warning("ODPM_IMAGE_PRUNE_STALE: %s", exc)
        return
    if parse_cache_tag(keep_tag) is None:
        _logger.debug(
            "ODPM_IMAGE_PRUNE_STALE: keep ref is not a cache-* tag: %s",
            keep_ref,
        )
        return

    if remote:
        tags = _crane_ls(repo)
        if tags is not None:
            stale = select_stale_cache_tags(tags, keep_tag=keep_tag)
            for tag in stale:
                _crane_delete(f"{repo}:{tag}")
                _docker_rmi(f"{repo}:{tag}")
            if stale:
                _logger.info(
                    "attempted prune of %s stale remote cache tag(s) "
                    "for %s (kept %s)",
                    len(stale),
                    repo,
                    keep_tag,
                )
        # Best-effort local even when crane is missing or ls failed.
        local_stale = select_stale_cache_tags(
            _docker_list_tags(repo), keep_tag=keep_tag
        )
        for tag in local_stale:
            _docker_rmi(f"{repo}:{tag}")
        return

    stale = select_stale_cache_tags(_docker_list_tags(repo), keep_tag=keep_tag)
    for tag in stale:
        _docker_rmi(f"{repo}:{tag}")
    if stale:
        _logger.info(
            "pruned %s stale local cache tag(s) for %s (kept %s)",
            len(stale),
            repo,
            keep_tag,
        )


__all__ = [
    "ODPM_IMAGE_PRUNE_STALE_ENV",
    "parse_cache_tag",
    "prune_stale_layer_cache_tags",
    "prune_stale_requested",
    "select_stale_cache_tags",
    "split_image_ref",
]
