from __future__ import annotations

import os
import pathlib
from typing import TYPE_CHECKING, Literal

from .. import constants

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink


class ProjectDiscovery:
    def __init__(self, link: HandleOdooProjectLink) -> None:
        self.link = link

    def get_project_type(self) -> Literal["module", "project", "platform"]:
        project_type = constants.TYPE_PROJECT_PROJECT
        if os.path.exists(os.path.join(self.link.project_path, "__manifest__.py")):
            project_type = constants.TYPE_PROJECT_MODULE
        return project_type

    def update_project_type(self) -> None:
        self.link.project_data.project_type = self.get_project_type()

    def apply_inside_docker_path(self) -> None:
        project_type = self.get_project_type()
        self.link.inside_docker_path = self.link.project_data.name
        if project_type == constants.TYPE_PROJECT_MODULE:
            self.link.inside_docker_path = str(
                pathlib.PurePosixPath(
                    self.link.inside_docker_path, self.link.project_data.name
                )
            )
