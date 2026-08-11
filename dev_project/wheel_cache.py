"""Shared pip/uv download cache across odpm projects on one host."""

from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping
from typing import TYPE_CHECKING

from . import constants

if TYPE_CHECKING:
    from .project_env.types import MappedPath


def resolve_cache_root(env: Mapping[str, str] | None = None) -> str:
    """Return host wheel-cache root from env or ``~/.odpm/cache``."""
    source = env if env is not None else os.environ
    raw = (source.get(constants.ODPM_WHEEL_CACHE_ROOT_ENV) or "").strip()
    if raw:
        return os.path.abspath(os.path.expanduser(raw))
    return os.path.join(
        os.path.expanduser("~"),
        constants.CONFIG_DIR_IN_HOME_DIR,
        constants.DEFAULT_WHEEL_CACHE_DIRNAME,
    )


def container_uv_cache_dir() -> str:
    return os.path.join(
        constants.WHEEL_CACHE_CONTAINER_ROOT, constants.WHEEL_CACHE_UV_SUBDIR
    )


def container_pip_cache_dir(python_version: str) -> str:
    return os.path.join(
        constants.WHEEL_CACHE_CONTAINER_ROOT,
        constants.WHEEL_CACHE_WHEELS_SUBDIR,
        python_version,
    )


def host_uv_cache_dir(cache_root: str) -> str:
    return os.path.join(cache_root, constants.WHEEL_CACHE_UV_SUBDIR)


def host_pip_cache_dir(cache_root: str, python_version: str) -> str:
    return os.path.join(
        cache_root, constants.WHEEL_CACHE_WHEELS_SUBDIR, python_version
    )


def use_container_cache_layout(env: Mapping[str, str] | None = None) -> bool:
    """True when the compose mount root ``/cache/odpm`` is present."""
    del env  # reserved for future explicit overrides
    return os.path.isdir(constants.WHEEL_CACHE_CONTAINER_ROOT)


def resolve_wheel_cache_env(
    *,
    python_version: str,
    env: Mapping[str, str] | None = None,
    mkdir: bool = True,
) -> dict[str, str]:
    """Return ``PIP_CACHE_DIR`` / ``UV_CACHE_DIR`` when not already set.

    Explicit ``PIP_CACHE_DIR`` / ``UV_CACHE_DIR`` in *env* (or ``os.environ``)
    are never overridden. Missing dirs are created when *mkdir* is true.
    """
    source = env if env is not None else os.environ
    result: dict[str, str] = {}

    if use_container_cache_layout(source):
        pip_dir = container_pip_cache_dir(python_version)
        uv_dir = container_uv_cache_dir()
    else:
        cache_root = resolve_cache_root(source)
        pip_dir = host_pip_cache_dir(cache_root, python_version)
        uv_dir = host_uv_cache_dir(cache_root)

    if not (source.get(constants.PIP_CACHE_DIR_ENV) or "").strip():
        result[constants.PIP_CACHE_DIR_ENV] = pip_dir
    if not (source.get(constants.UV_CACHE_DIR_ENV) or "").strip():
        result[constants.UV_CACHE_DIR_ENV] = uv_dir

    if mkdir:
        for path in result.values():
            os.makedirs(path, exist_ok=True)
    return result


def apply_wheel_cache_env(
    *,
    python_version: str,
    env: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    """Merge resolved wheel-cache paths into *env* (default ``os.environ``)."""
    target: MutableMapping[str, str] = env if env is not None else os.environ
    resolved = resolve_wheel_cache_env(python_version=python_version, env=target)
    target.update(resolved)
    return dict(resolved)


def host_cache_mounts(
    *,
    python_version: str,
    cache_root: str | None = None,
    env: Mapping[str, str] | None = None,
) -> list[MappedPath]:
    """Host→container mounts for shared uv and pip wheel caches."""
    from .project_env.types import MappedPath

    root = cache_root if cache_root is not None else resolve_cache_root(env)
    host_uv = host_uv_cache_dir(root)
    host_pip = host_pip_cache_dir(root, python_version)
    os.makedirs(host_uv, exist_ok=True)
    os.makedirs(host_pip, exist_ok=True)
    return [
        MappedPath(local=host_uv, docker=container_uv_cache_dir()),
        MappedPath(local=host_pip, docker=container_pip_cache_dir(python_version)),
    ]
