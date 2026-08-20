"""Track which runtime Unix identity a project base image was built for."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants

if TYPE_CHECKING:
    from ..config.config import Config


def base_image_identity_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.BASE_IMAGE_IDENTITY_REL_PATH)


def project_dockerfile_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.DOCKERFILE)


def dockerfile_content_sha256(project_dir: str) -> str:
    path = project_dockerfile_path(project_dir)
    if not os.path.isfile(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as reader:
        for chunk in iter(lambda: reader.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_base_image_identity(
    config: Config, *, image_ref: str | None = None
) -> dict[str, str]:
    policy = config.policy
    identity = {
        "user": policy.runtime_unix_user(),
        "uid": policy.runtime_unix_uid(),
        "gid": policy.runtime_unix_gid(),
        "base_image_profile": policy.base_image_profile,
        "dockerfile_sha256": dockerfile_content_sha256(config.project_dir),
    }
    if image_ref:
        identity["image_ref"] = image_ref
    return identity


def read_base_image_identity(project_dir: str) -> dict[str, str] | None:
    path = base_image_identity_path(project_dir)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as reader:
        payload: dict[str, Any] = json.load(reader)
    required = ("user", "uid", "gid", "base_image_profile", "dockerfile_sha256")
    if not all(isinstance(payload.get(key), str) for key in required):
        return None
    identity = {key: payload[key] for key in required}
    image_ref = payload.get("image_ref")
    if isinstance(image_ref, str) and image_ref:
        identity["image_ref"] = image_ref
    return identity


def write_base_image_identity(project_dir: str, identity: dict[str, str]) -> None:
    ensure_base_image_identity_gitignore(project_dir)
    path = base_image_identity_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as writer:
        json.dump(identity, writer, indent=2, sort_keys=True)
        writer.write("\n")


def ensure_base_image_identity_gitignore(project_dir: str) -> None:
    """Keep machine-local identity stamp out of version control."""
    odpm_dir = os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY)
    os.makedirs(odpm_dir, exist_ok=True)
    gitignore_path = os.path.join(odpm_dir, ".gitignore")
    entry = "base_image_identity.json"
    if not os.path.isfile(gitignore_path):
        Path(gitignore_path).write_text(f"{entry}\n", encoding="utf-8")
        return
    existing = Path(gitignore_path).read_text(encoding="utf-8")
    if entry not in existing.splitlines():
        suffix = "" if existing.endswith("\n") or not existing else "\n"
        Path(gitignore_path).write_text(f"{existing}{suffix}{entry}\n", encoding="utf-8")


def base_image_identity_matches(
    config: Config, *, image_ref: str | None = None
) -> bool:
    stamp = read_base_image_identity(config.project_dir)
    if stamp is None:
        return False
    expected = expected_base_image_identity(config, image_ref=image_ref)
    if image_ref is None:
        # Ignore optional image_ref in stamp when caller does not care.
        stamp = {key: value for key, value in stamp.items() if key != "image_ref"}
        expected = {
            key: value for key, value in expected.items() if key != "image_ref"
        }
    return stamp == expected


def base_image_identity_matches_host(host_ctx) -> bool:
    stamp = read_base_image_identity(host_ctx.project_dir)
    if stamp is None:
        return False
    policy = host_ctx.policy
    expected = {
        "user": policy.runtime_unix_user(),
        "uid": policy.runtime_unix_uid(),
        "gid": policy.runtime_unix_gid(),
        "base_image_profile": policy.base_image_profile,
        "dockerfile_sha256": dockerfile_content_sha256(host_ctx.project_dir),
    }
    return stamp == expected
