from dataclasses import dataclass
from typing import Literal

HTTP_MARKER = "http"
GIT_MARKER = "git"
SSH_MARKER = "ssh"
FILE_SYSTEM_MARKER = "file://"


@dataclass
class OdooProjectData(object):
    server: str
    author: str
    name: str
    git_name: str
    commit: str
    branch: str
    system_type: Literal["developing", "platform", "standart"]
    relative_path: str
    project_type: Literal["module", "project", "platform"]
    type: Literal["http", "git", "local_filesystem", "ssh"]
