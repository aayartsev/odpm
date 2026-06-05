from __future__ import annotations

import os
import pathlib
import re
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse

from .. import constants
from .types import (
    FILE_SYSTEM_MARKER,
    GIT_MARKER,
    HTTP_MARKER,
    SSH_MARKER,
    OdooProjectData,
)

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink


class LinkParser:
    def __init__(self, link: HandleOdooProjectLink) -> None:
        self.link = link

    def parse_project_string(self) -> None:
        project_data = self.link.project_string.split(" ")
        index_of_link = 0
        for marker in [HTTP_MARKER, GIT_MARKER, FILE_SYSTEM_MARKER]:
            for i in range(len(project_data)):
                if marker in project_data[i]:
                    self.link.project_link = project_data[i]
                    index_of_link = i
        for git_marker in [HTTP_MARKER, GIT_MARKER, SSH_MARKER]:
            if git_marker in self.link.project_link:
                self.link.gitlink = self.link.project_link
        if index_of_link == 1 and len(project_data) > 2:
            self.link.branch = project_data[2]
            self.link.branch_explicit = True
        if index_of_link == 1 and len(project_data) > 3:
            self.link.commit = project_data[3]
            self.link.commit_explicit = True
        if index_of_link == 0 and len(project_data) > 1:
            self.link.branch = project_data[1]
            self.link.branch_explicit = True
        if index_of_link == 0 and len(project_data) > 2:
            self.link.commit = project_data[2]
            self.link.commit_explicit = True

    def get_git_link_type(self) -> Literal["http", "git", "local_filesystem", "ssh"]:
        project_link_type = constants.GITLINK_TYPE_FILE
        if FILE_SYSTEM_MARKER in self.link.project_link:
            return constants.GITLINK_TYPE_FILE
        if HTTP_MARKER in self.link.project_link:
            return constants.GITLINK_TYPE_HTTP
        if SSH_MARKER in self.link.project_link:
            return constants.GITLINK_TYPE_SSH
        git_pattern = re.findall(self.link.git_regex, self.link.project_link)
        if git_pattern:
            project_link_type = constants.GITLINK_TYPE_GIT
        return project_link_type

    def parse_link_by_type(self) -> OdooProjectData:
        return getattr(self, f"parse_{self.link.link_type}")()

    def parse_local_filesystem(self) -> OdooProjectData:
        local_path = self.link.project_link.replace("file://", "")
        if local_path:
            if local_path[-1] == "/":
                local_path = local_path[:-1]

            project_name = os.path.basename(local_path)
            return OdooProjectData(
                server="",
                author="",
                name=project_name,
                git_name=project_name,
                commit=self.link.commit,
                branch=self.link.branch,
                relative_path="",
                system_type=self.link.system_type,
                project_type="project",
                type=constants.GITLINK_TYPE_FILE,
            )
        return OdooProjectData(
            server="",
            author="",
            name="",
            git_name="",
            commit=self.link.commit,
            branch=self.link.branch,
            relative_path="",
            system_type=self.link.system_type,
            project_type="project",
            type=constants.GITLINK_TYPE_FILE,
        )

    def parse_http(self) -> OdooProjectData:
        server = self.link.project_link.split("/")[2]
        if ":" in server:
            server = server.split(":")[0]
        author = self.link.project_link.split("/")[3]
        relative_path = (
            self.link.project_link.replace("http://", "")
            .replace("https://", "")
            .replace(".git", "")
        )
        if ".git" in self.link.project_link:
            project_name = self.link.project_link.split("/")[-1].replace(".git", "")
            return OdooProjectData(
                server=server,
                author=author,
                name=project_name,
                git_name=project_name,
                commit=self.link.commit,
                branch=self.link.branch,
                relative_path=relative_path,
                system_type=self.link.system_type,
                project_type="project",
                type=constants.GITLINK_TYPE_HTTP,
            )
        project_name = os.path.join(*self.link.project_link.split("/")[3:])
        project_name = os.path.basename(project_name)
        return OdooProjectData(
            server=server,
            author="",
            name=f"http_project_{project_name}",
            git_name=project_name,
            commit=self.link.commit,
            branch=self.link.branch,
            relative_path=relative_path,
            system_type=self.link.system_type,
            project_type="project",
            type=constants.GITLINK_TYPE_SSH,
        )

    def parse_ssh(self) -> OdooProjectData:
        parsed_link = urlparse(self.link.project_link)
        server = parsed_link.netloc
        if ":" in server:
            server = server.split(":")[0]
        relative_path = parsed_link.path
        if ".git" in relative_path:
            relative_path = relative_path.replace(".git", "")
        project_name = os.path.basename(os.path.join(*relative_path.split("/")))
        parsed_link = urlparse(self.link.project_link)
        hostname = parsed_link.hostname
        relative_path = f"{hostname}{parsed_link.path}"
        if ".git" in relative_path:
            relative_path = relative_path.replace(".git", "")
        return OdooProjectData(
            server=server,
            author="",
            name=f"ssh_project_{project_name}",
            git_name=project_name,
            commit=self.link.commit,
            branch=self.link.branch,
            relative_path=relative_path,
            system_type=self.link.system_type,
            project_type="project",
            type=constants.GITLINK_TYPE_SSH,
        )

    def parse_git(self) -> OdooProjectData:
        server = self.link.project_link.split(":")[0].split("@")[1]
        author = self.link.project_link.split(":")[1].split("/")[0]
        project_name = self.link.project_link.split(":")[1].split("/")[1].replace(".git", "")
        hostname = self.link.project_link.split("@")[1].split(":")[0]
        uri_path = self.link.project_link.split(":")[1].replace(".git", "")
        relative_path = f"{hostname}/{uri_path}"
        return OdooProjectData(
            server=server,
            author=author,
            name=project_name,
            git_name=project_name,
            commit=self.link.commit,
            branch=self.link.branch,
            system_type=self.link.system_type,
            project_type="project",
            relative_path=relative_path,
            type=constants.GITLINK_TYPE_GIT,
        )

    def get_project_path(self) -> str:
        if self.link.link_type in [
            constants.GITLINK_TYPE_SSH,
            constants.GITLINK_TYPE_GIT,
            constants.GITLINK_TYPE_HTTP,
        ]:
            if self.link.link_type == constants.GITLINK_TYPE_SSH:
                os.environ["GIT_SSH_VARIANT"] = "ssh"
            return os.path.abspath(
                os.path.join(
                    self.link.start_dir_to_clone, self.link.project_data.relative_path
                )
            )
        local_path = self.link.project_link.replace("file://", "")
        if local_path and self.link.link_type in [constants.GITLINK_TYPE_FILE]:
            if local_path[-1] == "/":
                local_path = local_path[:-1]
        return local_path

    def get_dir_to_clone(self) -> None:
        self.link.dir_to_clone = pathlib.Path(self.link.project_path).parent.absolute()
