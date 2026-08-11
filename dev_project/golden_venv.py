"""Golden core virtualenv store keyed by ``venv_lock_hash``."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import time
from collections.abc import Mapping
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from . import constants
from .logging import get_module_logger

if TYPE_CHECKING:
    from .bake_venv import VenvInstallSpec
    from .project_env.types import MappedPath

_logger = get_module_logger(__name__)


def golden_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return whether golden core venv is enabled (default: on)."""
    source = env if env is not None else os.environ
    raw = (source.get(constants.ODPM_GOLDEN_VENV_ENV) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def resolve_golden_root_for_host(env: Mapping[str, str] | None = None) -> str:
    """Always resolve the host-side golden root (ignore container mount)."""
    source = env if env is not None else os.environ
    raw = (source.get(constants.ODPM_GOLDEN_VENV_ROOT_ENV) or "").strip()
    if raw:
        return os.path.abspath(os.path.expanduser(raw))
    return os.path.join(
        os.path.expanduser("~"),
        constants.CONFIG_DIR_IN_HOME_DIR,
        constants.DEFAULT_GOLDEN_VENV_DIRNAME,
    )


def resolve_golden_root(env: Mapping[str, str] | None = None) -> str:
    """Host or container golden store root."""
    source = env if env is not None else os.environ
    if os.path.isdir(constants.GOLDEN_VENV_CONTAINER_ROOT):
        return constants.GOLDEN_VENV_CONTAINER_ROOT
    return resolve_golden_root_for_host(source)


def golden_path(lock_hash: str, *, root: str | None = None) -> str:
    base = root if root is not None else resolve_golden_root()
    return os.path.join(base, lock_hash)


def golden_venv_dir(lock_hash: str, *, root: str | None = None) -> str:
    return os.path.join(
        golden_path(lock_hash, root=root), constants.GOLDEN_VENV_DIR_NAME
    )


def golden_exists(lock_hash: str, *, root: str | None = None) -> bool:
    path = golden_path(lock_hash, root=root)
    incomplete = os.path.join(path, constants.GOLDEN_INCOMPLETE_BASENAME)
    if os.path.isfile(incomplete):
        return False
    venv_dir = os.path.join(path, constants.GOLDEN_VENV_DIR_NAME)
    lock_file = os.path.join(path, constants.GOLDEN_LOCK_BASENAME)
    if not os.path.isdir(venv_dir) or not os.path.isfile(lock_file):
        return False
    with open(lock_file, encoding="utf-8") as handle:
        return handle.read().strip() == lock_hash


def _incomplete_marker_path(golden_dir: str) -> str:
    return os.path.join(golden_dir, constants.GOLDEN_INCOMPLETE_BASENAME)


def _mark_incomplete(golden_dir: str) -> None:
    os.makedirs(golden_dir, exist_ok=True)
    with open(_incomplete_marker_path(golden_dir), "w", encoding="utf-8") as handle:
        handle.write("1\n")


def _clear_incomplete(golden_dir: str) -> None:
    path = _incomplete_marker_path(golden_dir)
    if os.path.isfile(path):
        os.unlink(path)

def host_golden_mounts(
    *,
    cache_root: str | None = None,
    env: Mapping[str, str] | None = None,
) -> list[MappedPath]:
    """Mount golden store root into the container."""
    from .project_env.types import MappedPath

    host_root = (
        cache_root
        if cache_root is not None
        else resolve_golden_root_for_host(env)
    )
    os.makedirs(host_root, exist_ok=True)
    return [
        MappedPath(local=host_root, docker=constants.GOLDEN_VENV_CONTAINER_ROOT),
    ]


@contextmanager
def _populate_lock(golden_dir: str) -> Iterator[None]:
    os.makedirs(golden_dir, exist_ok=True)
    lock_path = os.path.join(golden_dir, constants.GOLDEN_POPULATE_LOCK_BASENAME)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _write_meta(golden_dir: str, meta: dict[str, Any]) -> None:
    path = os.path.join(golden_dir, constants.GOLDEN_META_BASENAME)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _write_lock(golden_dir: str, lock_hash: str) -> None:
    path = os.path.join(golden_dir, constants.GOLDEN_LOCK_BASENAME)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(lock_hash)


def write_core_freeze(venv_dir: str, freeze_path: str) -> None:
    from .bake_venv import venv_python_path

    python_path = venv_python_path(venv_dir)
    result = subprocess.run(
        [python_path, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _logger.warning(
            "pip freeze for golden core failed (exit %s): %s",
            result.returncode,
            (result.stderr or "").strip(),
        )
        return
    parent = os.path.dirname(freeze_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(freeze_path, "w", encoding="utf-8") as handle:
        handle.write(result.stdout)


def _clonevirtualenv_available() -> bool:
    try:
        result = subprocess.run(
            [os.environ.get("PYTHON", "python3"), "-m", "clonevirtualenv", "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _try_clonevirtualenv(src_venv: str, dest_venv: str) -> bool:
    if not _clonevirtualenv_available():
        return False
    parent = os.path.dirname(dest_venv)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.exists(dest_venv):
        shutil.rmtree(dest_venv)
    result = subprocess.run(
        [
            os.environ.get("PYTHON", "python3"),
            "-m",
            "clonevirtualenv",
            src_venv,
            dest_venv,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _logger.info(
            "clonevirtualenv failed (exit %s); trying freeze install",
            result.returncode,
        )
        return False
    return os.path.isdir(dest_venv)


def _gevent_specs_from_freeze(freeze_path: str) -> list[str]:
    specs: list[str] = []
    with open(freeze_path, encoding="utf-8") as handle:
        for line in handle:
            package = line.split("#", 1)[0].strip()
            if package and "gevent" in package.lower():
                specs.append(package)
    return specs


def _install_from_freeze(
    *,
    freeze_path: str,
    project_dir: str,
    venv_dir: str,
    python_version: str,
    use_uv: bool,
) -> bool:
    from .bake_venv import (
        UV_PIP_INSTALL_OPTIONS,
        VenvInstallSpec,
        create_venv,
        run_pip_command,
        venv_python_path,
    )

    if not os.path.isfile(freeze_path):
        return False
    spec = VenvInstallSpec(
        project_dir=project_dir,
        venv_dir=venv_dir,
        odoo_requirements_path=freeze_path,
        extra_packages=[],
        python_version=python_version,
    )
    if os.path.exists(venv_dir):
        shutil.rmtree(venv_dir)
    create_venv(spec, use_uv=use_uv)
    python_path = venv_python_path(venv_dir)
    try:
        for gevent_spec in _gevent_specs_from_freeze(freeze_path):
            # Match install_odoo_requirement_packages: gevent needs no-build-isolation.
            normalized = gevent_spec.replace("<", "=").replace(">", "=")
            if use_uv:
                gevent_cmd = [
                    "uv",
                    "pip",
                    "install",
                    *UV_PIP_INSTALL_OPTIONS,
                    "--python",
                    python_path,
                    normalized,
                    "--no-build-isolation",
                ]
            else:
                gevent_cmd = [
                    python_path,
                    "-m",
                    "pip",
                    "install",
                    normalized,
                    "--no-build-isolation",
                ]
            run_pip_command(
                gevent_cmd, cwd=project_dir, python_version=python_version
            )
        if use_uv:
            cmd = [
                "uv",
                "pip",
                "install",
                *UV_PIP_INSTALL_OPTIONS,
                "--python",
                python_path,
                "-r",
                freeze_path,
            ]
        else:
            cmd = [python_path, "-m", "pip", "install", "-r", freeze_path]
        run_pip_command(cmd, cwd=project_dir, python_version=python_version)
    except Exception:
        _logger.info(
            "freeze install into %s failed; falling back to full core install",
            venv_dir,
            exc_info=True,
        )
        return False
    return True


def materialize_golden(
    spec: VenvInstallSpec,
    lock_hash: str,
    *,
    root: str | None = None,
    use_uv: bool | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    """Install core requirements into the golden store for *lock_hash*."""
    from .bake_venv import VenvInstallSpec, install_core_fresh

    base = root if root is not None else resolve_golden_root()
    golden_dir = golden_path(lock_hash, root=base)
    with _populate_lock(golden_dir):
        if golden_exists(lock_hash, root=base):
            return golden_dir
        _mark_incomplete(golden_dir)
        try:
            venv_dir = os.path.join(golden_dir, constants.GOLDEN_VENV_DIR_NAME)
            if os.path.exists(venv_dir):
                shutil.rmtree(venv_dir)
            golden_spec = VenvInstallSpec(
                project_dir=spec.project_dir,
                venv_dir=venv_dir,
                odoo_requirements_path=spec.odoo_requirements_path,
                extra_packages=[],
                python_version=spec.python_version,
                bootstrap_packages=list(spec.bootstrap_packages),
            )
            # Write .lock only after freeze/meta so peers do not clone a partial store.
            install_core_fresh(
                golden_spec,
                use_uv=use_uv,
                lock_file_path=None,
                lock_hash=None,
            )
            freeze_path = os.path.join(
                golden_dir, constants.GOLDEN_CORE_FREEZE_BASENAME
            )
            write_core_freeze(venv_dir, freeze_path)
            payload = {
                "python_version": spec.python_version,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "odpm_version": getattr(constants, "ODPM_VERSION", ""),
            }
            if meta:
                payload.update(meta)
            _write_meta(golden_dir, payload)
            _write_lock(golden_dir, lock_hash)
        finally:
            _clear_incomplete(golden_dir)
    return golden_dir


def clone_golden_to_project(
    golden_dir: str,
    project_venv_dir: str,
    *,
    python_version: str,
    project_dir: str,
    use_uv: bool,
) -> bool:
    """Clone golden core into *project_venv_dir*. Return True on success."""
    src_venv = os.path.join(golden_dir, constants.GOLDEN_VENV_DIR_NAME)
    if not os.path.isdir(src_venv):
        return False
    if os.path.isfile(os.path.join(golden_dir, constants.GOLDEN_INCOMPLETE_BASENAME)):
        return False
    if os.path.exists(project_venv_dir):
        shutil.rmtree(project_venv_dir)
    if _try_clonevirtualenv(src_venv, project_venv_dir):
        return True
    freeze_path = os.path.join(golden_dir, constants.GOLDEN_CORE_FREEZE_BASENAME)
    return _install_from_freeze(
        freeze_path=freeze_path,
        project_dir=project_dir,
        venv_dir=project_venv_dir,
        python_version=python_version,
        use_uv=use_uv,
    )


def populate_golden_from_project(
    project_venv_dir: str,
    lock_hash: str,
    *,
    root: str | None = None,
    python_version: str,
    project_dir: str,
    use_uv: bool,
    meta: dict[str, Any] | None = None,
) -> str | None:
    """Copy a core-only project venv into the golden store (before extras)."""
    base = root if root is not None else resolve_golden_root()
    golden_dir = golden_path(lock_hash, root=base)
    with _populate_lock(golden_dir):
        if golden_exists(lock_hash, root=base):
            return golden_dir
        _mark_incomplete(golden_dir)
        try:
            dest_venv = os.path.join(golden_dir, constants.GOLDEN_VENV_DIR_NAME)
            if os.path.exists(dest_venv):
                shutil.rmtree(dest_venv)
            cloned = _try_clonevirtualenv(project_venv_dir, dest_venv)
            freeze_path = os.path.join(
                golden_dir, constants.GOLDEN_CORE_FREEZE_BASENAME
            )
            if not cloned:
                write_core_freeze(project_venv_dir, freeze_path)
                if not _install_from_freeze(
                    freeze_path=freeze_path,
                    project_dir=project_dir,
                    venv_dir=dest_venv,
                    python_version=python_version,
                    use_uv=use_uv,
                ):
                    _logger.warning(
                        "Could not populate golden venv for hash %s", lock_hash
                    )
                    return None
            else:
                write_core_freeze(dest_venv, freeze_path)
            _write_lock(golden_dir, lock_hash)
            payload = {
                "python_version": python_version,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "odpm_version": getattr(constants, "ODPM_VERSION", ""),
            }
            if meta:
                payload.update(meta)
            _write_meta(golden_dir, payload)
        finally:
            _clear_incomplete(golden_dir)
    return golden_dir
