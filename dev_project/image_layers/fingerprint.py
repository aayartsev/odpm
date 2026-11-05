"""Layer fingerprints schema v1 (ADR-027)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .family import family_for_profile

FINGERPRINT_SCHEMA_VERSION = 1


def _sha8(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:8]


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _template_path(program_dir: str, name: str) -> Path:
    return Path(program_dir) / "dev_project" / "templates" / name


def _profile(config: Any) -> str:
    return str(getattr(config.policy, "base_image_profile", "") or "")


def _lock_sha_map(config: Any) -> dict[str, str]:
    """Return name→commit from the active lock source after prepare."""
    from ..git.deps_lock import deps_lock_path, load_deps_lock
    from ..manifest.locks import (
        LockSource,
        manifest_git_locks_from_view,
        resolve_lock_source_from_view,
    )

    project_dir = config.project_dir
    bootstrap = getattr(config, "bootstrap", None)
    view = getattr(bootstrap, "manifest_view", None) if bootstrap is not None else None
    source = resolve_lock_source_from_view(view)
    if source == LockSource.MANIFEST and view is not None:
        locks = manifest_git_locks_from_view(view)
        return {str(k): str(v) for k, v in locks.items() if v}
    path = Path(deps_lock_path(project_dir))
    if not path.is_file():
        return {}
    try:
        lock = load_deps_lock(path)
    except ValueError:
        return {}
    out: dict[str, str] = {}
    if lock.platform is not None and lock.platform.commit:
        out["platform"] = str(lock.platform.commit)
    for entry in lock.dependencies or []:
        if entry.commit:
            # Stable key: canonical URL (dependencies have no short names in file lock).
            out[str(entry.url)] = str(entry.commit)
    return out


def compute_platform_fingerprint(config: Any, *, program_dir: str) -> str:
    df = _template_path(program_dir, "dockerfile_platform")
    extras = sorted(
        r.strip() for r in (getattr(config, "requirements_txt", None) or []) if r.strip()
    )
    locks = _lock_sha_map(config)
    platform_sha = locks.get("platform", "")
    payload = {
        "schema": FINGERPRINT_SCHEMA_VERSION,
        "odoo_version": str(config.odoo_version),
        "build_date": str(getattr(config, "odoo_build_date", "") or ""),
        "profile": _profile(config),
        "extras": extras,
        "platform_git_sha": platform_sha,
        "dockerfile_platform": _sha8(df.read_bytes()) if df.is_file() else "missing",
        "python": str(config.python_version),
        "distro": f"{config.distro_name}-{config.distro_version}",
        "arch": str(config.arch),
        "venv_mode": str(getattr(config.policy, "venv_mode", "baked")),
    }
    return _sha8(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def compute_deps_fingerprint(
    config: Any, *, program_dir: str, platform_ref: str
) -> str | None:
    locks = _lock_sha_map(config)
    dep_shas = {
        name: sha
        for name, sha in sorted(locks.items())
        if name != "platform"
    }
    if not dep_shas:
        return None
    df = _template_path(program_dir, "dockerfile_deps")
    payload = {
        "schema": FINGERPRINT_SCHEMA_VERSION,
        "platform_ref": platform_ref,
        "dependencies": dep_shas,
        "dockerfile_deps": _sha8(df.read_bytes()) if df.is_file() else "missing",
    }
    return _sha8(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def compute_app_fingerprint(
    config: Any,
    *,
    program_dir: str,
    parent_ref: str,
    developing_git_sha: str,
    secrets_baked: bool,
) -> str:
    df = _template_path(program_dir, "dockerfile_app")
    payload = {
        "schema": FINGERPRINT_SCHEMA_VERSION,
        "parent_ref": parent_ref,
        "dockerfile_app": _sha8(df.read_bytes()) if df.is_file() else "missing",
        "secrets_baked": bool(secrets_baked),
        "developing_git_sha": developing_git_sha,
    }
    return _sha8(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def compute_lint_fingerprint(
    config: Any, *, program_dir: str, platform_fp: str
) -> str:
    project = Path(config.project_dir)
    pre_commit = project / ".pre-commit-config.yaml"
    hooks = project / ".pre-commit-hooks.yaml"
    df = _template_path(program_dir, "dockerfile_lint")
    bake = Path(program_dir) / "dev_project" / "bake_pre_commit.py"
    payload = {
        "schema": FINGERPRINT_SCHEMA_VERSION,
        "platform_fp": platform_fp,
        "dockerfile_lint": _sha8(df.read_bytes()) if df.is_file() else "missing",
        "bake_pre_commit": (
            _sha8(bake.read_bytes()) if bake.is_file() else "missing"
        ),
        "pre_commit_config": _sha256_file(pre_commit),
        "pre_commit_hooks": (
            _sha256_file(hooks) if hooks.is_file() else "absent"
        ),
    }
    return _sha8(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def layer_image_ref(
    config: Any,
    *,
    layer: str,
    fingerprint: str,
    registry: str | None = None,
) -> str:
    import os

    reg = registry or os.environ.get("ODPM_BASE_IMAGE_REGISTRY") or os.environ.get(
        "CI_REGISTRY_IMAGE", ""
    )
    if not reg:
        # Local-only tag when no registry configured.
        reg = f"odpm-local/{getattr(config, 'project_name', 'project')}"
    profile = _profile(config)
    family = family_for_profile(profile)
    ver = str(config.odoo_version)
    build_date = str(getattr(config, "odoo_build_date", "") or "unknown")
    tag = f"cache-{layer}-{family}-{ver}-{build_date}-v-{fingerprint}"
    return f"{reg}:{tag}"


# Re-export for callers
__all__ = [
    "FINGERPRINT_SCHEMA_VERSION",
    "compute_app_fingerprint",
    "compute_deps_fingerprint",
    "compute_lint_fingerprint",
    "compute_platform_fingerprint",
    "family_for_profile",
    "layer_image_ref",
]
