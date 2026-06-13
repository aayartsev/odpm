"""Debug profile preview for odpm plan step evaluation and diffs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from .. import constants
from ..project_env.debug_profile import DebuggerProfile, DebuggerProfileBuilder

if TYPE_CHECKING:
    from ..config import Config
    from ..project_env import CreateProjectEnvironment


def format_debug_profile_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=4) + "\n"


def preview_debug_profile_text(project_env: CreateProjectEnvironment) -> str | None:
    try:
        profile = DebuggerProfileBuilder(project_env).build()
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    return format_debug_profile_payload(profile.to_dict())


def normalized_debug_profile_text_from_disk(project_dir: str) -> str:
    path = os.path.join(project_dir, constants.ODPM_DEBUG_PROFILE_REL_PATH)
    if not os.path.isfile(path):
        return ""
    try:
        raw_text = Path(path).read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        if not isinstance(payload, dict):
            return ""
        profile = DebuggerProfile.from_dict(payload)
        return format_debug_profile_payload(profile.to_dict())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return ""


def debug_profile_needs_update(
    config: Config, project_env: CreateProjectEnvironment | None
) -> tuple[bool, str]:
    if project_env is None:
        profile_path = os.path.join(
            config.project_dir, constants.ODPM_DEBUG_PROFILE_REL_PATH
        )
        if not os.path.isfile(profile_path):
            return True, "debug profile missing"
        return False, "debug profile on disk"

    preview = preview_debug_profile_text(project_env)
    if preview is None:
        return True, "unable to preview debug profile"
    on_disk = normalized_debug_profile_text_from_disk(config.project_dir)
    if preview != on_disk:
        return True, "debug profile payload changed"
    return False, "debug profile unchanged"
