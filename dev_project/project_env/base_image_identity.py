"""Track which runtime Unix identity a project base image was built for."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import constants

if TYPE_CHECKING:
    from ..config.config import Config


def base_image_identity_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.BASE_IMAGE_IDENTITY_REL_PATH)


def expected_base_image_identity(config: Config) -> dict[str, str]:
    policy = config.policy
    return {
        "user": policy.runtime_unix_user(),
        "uid": policy.runtime_unix_uid(),
        "gid": policy.runtime_unix_gid(),
    }


def read_base_image_identity(project_dir: str) -> dict[str, str] | None:
    path = base_image_identity_path(project_dir)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as reader:
        payload: dict[str, Any] = json.load(reader)
    user = payload.get("user")
    uid = payload.get("uid")
    gid = payload.get("gid")
    if not isinstance(user, str) or not isinstance(uid, str) or not isinstance(gid, str):
        return None
    return {"user": user, "uid": uid, "gid": gid}


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


def base_image_identity_matches(config: Config) -> bool:
    stamp = read_base_image_identity(config.project_dir)
    if stamp is None:
        return False
    return stamp == expected_base_image_identity(config)
