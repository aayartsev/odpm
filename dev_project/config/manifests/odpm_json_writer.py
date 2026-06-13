"""Write default odpm.json when project manifest is missing."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..types import OdpmJson

if TYPE_CHECKING:
    from ..config import Config


def rewrite_odpm_json(
    config: Config,
    *,
    create_default: Callable[[], OdpmJson],
) -> None:
    default_odpm_json_content = create_default()
    pathlib.Path(config.developing_project.project_path).mkdir(
        parents=True, exist_ok=True
    )
    with open(config.repo_odpm_json, "w", encoding="utf-8") as odpm_json_file:
        json.dump(
            default_odpm_json_content, odpm_json_file, ensure_ascii=False, indent=4
        )
