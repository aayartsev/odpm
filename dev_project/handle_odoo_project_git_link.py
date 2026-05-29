import os
import pathlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from . import constants, translations
from .inside_docker_app.logger import get_module_logger

_logger = get_module_logger(__name__)

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


class HandleOdooProjectLink:
    def __init__(
        self,
        project_string: str,
        path_to_ssh_key: str,
        start_dir_to_clone: str,
        system_type: Literal["developing", "platform", "standart"] = "standart",
    ):
        self.is_true = True
        if not project_string:
            self.is_true = False
        self.system_type: Literal["developing", "platform", "standart"] = system_type
        self.project_string = project_string
        self.project_link = ""
        self.gitlink = ""
        self.commit = ""
        self.branch = ""
        self.branch_explicit = False
        self.commit_explicit = False
        self.path_to_ssh_key = path_to_ssh_key
        self.start_dir_to_clone = start_dir_to_clone
        self.dir_to_clone = ""
        self.git_regex = r"git@[a-z._-]*:"
        self.parse_project_string()
        self.link_type = self.get_git_link_type()
        self.project_data = self.parse_link_by_type()
        self.project_path = self.get_project_path()
        self.update_project_type()
        self.is_cloned = False

    def build_project(self) -> None:
        if self.link_type in [
            constants.GITLINK_TYPE_HTTP,
            constants.GITLINK_TYPE_GIT,
            constants.GITLINK_TYPE_SSH,
        ]:
            self.get_dir_to_clone()
            self.check_project()
        if self.link_type in [constants.GITLINK_TYPE_FILE]:
            self.is_cloned = True
        project_type = self.get_project_type()
        self.inside_docker_path = self.project_data.name
        if project_type == constants.TYPE_PROJECT_MODULE:
            self.inside_docker_path = str(
                pathlib.PurePosixPath(self.inside_docker_path, self.project_data.name)
            )

    def parse_project_string(self) -> None:
        project_data = self.project_string.split(" ")
        index_of_link = 0
        for marker in [HTTP_MARKER, GIT_MARKER, FILE_SYSTEM_MARKER]:
            for i in range(len(project_data)):
                if marker in project_data[i]:
                    self.project_link = project_data[i]
                    index_of_link = i
        for git_marker in [HTTP_MARKER, GIT_MARKER, SSH_MARKER]:
            if git_marker in self.project_link:
                self.gitlink = self.project_link
        if index_of_link == 1 and len(project_data) > 2:
            self.branch = project_data[2]
            self.branch_explicit = True
        if index_of_link == 1 and len(project_data) > 3:
            self.commit = project_data[3]
            self.commit_explicit = True
        if index_of_link == 0 and len(project_data) > 1:
            self.branch = project_data[1]
            self.branch_explicit = True
        if index_of_link == 0 and len(project_data) > 2:
            self.commit = project_data[2]
            self.commit_explicit = True

    def get_git_link_type(self) -> Literal["http", "git", "local_filesystem", "ssh"]:
        project_link_type = constants.GITLINK_TYPE_FILE
        if FILE_SYSTEM_MARKER in self.project_link:
            project_link_type = constants.GITLINK_TYPE_FILE
            return project_link_type
        if HTTP_MARKER in self.project_link:
            project_link_type = constants.GITLINK_TYPE_HTTP
            return project_link_type
        if SSH_MARKER in self.project_link:
            project_link_type = constants.GITLINK_TYPE_SSH
            return project_link_type
        git_pattern = re.findall(self.git_regex, self.project_link)
        if git_pattern:
            project_link_type = constants.GITLINK_TYPE_GIT
        return project_link_type

    def parse_link_by_type(self) -> OdooProjectData:
        return getattr(self, f"parse_{self.link_type}")()

    def get_project_type(self) -> Literal["module", "project", "platform"]:
        project_type = constants.TYPE_PROJECT_PROJECT
        if os.path.exists(os.path.join(self.get_project_path(), "__manifest__.py")):
            project_type = constants.TYPE_PROJECT_MODULE
        return project_type

    def update_project_type(self) -> None:
        project_type = self.get_project_type()
        self.project_data.project_type = project_type

    def parse_local_filesystem(self) -> OdooProjectData:
        local_path = self.project_link.replace("file://", "")
        if local_path:
            if local_path[-1] == "/":
                local_path = local_path[:-1]

            project_name = os.path.basename(local_path)
            return OdooProjectData(
                server="",
                author="",
                name=project_name,
                git_name=project_name,
                commit=self.commit,
                branch=self.branch,
                relative_path="",
                system_type=self.system_type,
                project_type="project",
                type=constants.GITLINK_TYPE_FILE,
            )
        else:
            return OdooProjectData(
                server="",
                author="",
                name="",
                git_name="",
                commit=self.commit,
                branch=self.branch,
                relative_path="",
                system_type=self.system_type,
                project_type="project",
                type=constants.GITLINK_TYPE_FILE,
            )

    def parse_http(self) -> OdooProjectData:
        server = self.project_link.split("/")[2]
        if ":" in server:
            server = server.split(":")[0]
        author = self.project_link.split("/")[3]
        relative_path = (
            self.project_link.replace("http://", "")
            .replace("https://", "")
            .replace(".git", "")
        )
        if ".git" in self.project_link:
            project_name = self.project_link.split("/")[-1].replace(".git", "")
            return OdooProjectData(
                server=server,
                author=author,
                name=project_name,
                git_name=project_name,
                commit=self.commit,
                branch=self.branch,
                relative_path=relative_path,
                system_type=self.system_type,
                project_type="project",
                type=constants.GITLINK_TYPE_HTTP,
            )
        else:
            project_name = os.path.join(*self.project_link.split("/")[3:])
            project_name = os.path.basename(project_name)
            return OdooProjectData(
                server=server,
                author="",
                name=f"http_project_{project_name}",
                git_name=project_name,
                commit=self.commit,
                branch=self.branch,
                relative_path=relative_path,
                system_type=self.system_type,
                project_type="project",
                type=constants.GITLINK_TYPE_SSH,
            )

    def parse_ssh(self) -> OdooProjectData:
        parsed_link = urlparse(self.project_link)
        server = parsed_link.netloc
        if ":" in server:
            server = server.split(":")[0]
        relative_path = parsed_link.path
        if ".git" in relative_path:
            relative_path = relative_path.replace(".git", "")
        project_name = os.path.join(*relative_path.split("/"))
        project_name = os.path.basename(project_name)
        parsed_link = urlparse(self.project_link)
        hostname = parsed_link.hostname
        relative_path = f"{hostname}{parsed_link.path}"
        if ".git" in relative_path:
            relative_path = relative_path.replace(".git", "")
        return OdooProjectData(
            server=server,
            author="",
            name=f"ssh_project_{project_name}",
            git_name=project_name,
            commit=self.commit,
            branch=self.branch,
            relative_path=relative_path,
            system_type=self.system_type,
            project_type="project",
            type=constants.GITLINK_TYPE_SSH,
        )

    def parse_git(self) -> OdooProjectData:
        server = self.project_link.split(":")[0].split("@")[1]
        author = self.project_link.split(":")[1].split("/")[0]
        project_name = self.project_link.split(":")[1].split("/")[1].replace(".git", "")
        hostname = self.project_link.split("@")[1].split(":")[0]
        uri_path = self.project_link.split(":")[1].replace(".git", "")
        relative_path = f"{hostname}/{uri_path}"
        return OdooProjectData(
            server=server,
            author=author,
            name=project_name,
            git_name=project_name,
            commit=self.commit,
            branch=self.branch,
            system_type=self.system_type,
            project_type="project",
            relative_path=relative_path,
            type=constants.GITLINK_TYPE_GIT,
        )

    def get_project_path(self) -> str:
        if self.link_type in [
            constants.GITLINK_TYPE_SSH,
            constants.GITLINK_TYPE_GIT,
            constants.GITLINK_TYPE_HTTP,
        ]:
            if self.link_type == constants.GITLINK_TYPE_SSH:
                os.environ["GIT_SSH_VARIANT"] = "ssh"
            return os.path.abspath(
                os.path.join(self.start_dir_to_clone, self.project_data.relative_path)
            )
        local_path = self.project_link.replace("file://", "")
        if local_path:
            if self.link_type in [constants.GITLINK_TYPE_FILE]:
                if local_path[-1] == "/":
                    local_path = local_path[:-1]
        return local_path

    def get_dir_to_clone(self) -> None:
        self.dir_to_clone = pathlib.Path(self.project_path).parent.absolute()

    def check_project(self) -> None:
        state = False
        repo_is_same = False
        project_dir_name = os.path.basename(self.project_path)
        new_destination = os.path.join(
            self.dir_to_clone, f"new_project_{project_dir_name}"
        )
        if self.link_type == constants.GITLINK_TYPE_HTTP and ".git" not in self.gitlink:
            if os.path.exists(new_destination):
                self.project_path = new_destination
        if os.path.exists(self.project_path):
            if os.path.exists(os.path.join(self.project_path, ".git")):
                os.chdir(self.project_path)
                state = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"], capture_output=True
                )
                if b"true" in state.stdout:
                    repo_is_same = self.check_repo_url(
                        self.get_project_path(), self.project_string
                    )
        if not state or b"true" not in state.stdout or not repo_is_same:
            self.force_clone_repo()
        else:
            self.is_cloned = True
        if (
            project_dir_name in ["odoo"]
            and not os.path.exists(new_destination)
            and self.system_type != "platform"
        ):
            os.rename(self.project_path, new_destination)
            self.project_path = new_destination

    def force_clone_repo(self) -> None:
        try:
            shutil.rmtree(self.project_path)
        except FileNotFoundError:
            pass
        if not os.path.exists(self.dir_to_clone):
            os.makedirs(self.dir_to_clone)
        os.chdir(self.dir_to_clone)
        self.clone_repo()

    def clone_repo(self) -> None:
        if self.system_type != "platform":
            if not self.path_to_ssh_key:
                clone_results = subprocess.run(
                    ["git", "clone", self.gitlink], capture_output=False
                )
            else:
                clone_results = subprocess.run(
                    f"""git clone {self.gitlink} --config core.sshCommand="ssh -i {self.path_to_ssh_key}" """,
                    capture_output=False,
                    shell=True,
                )
            if clone_results.stderr:
                clone_results_error_string = clone_results.stderr.decode(
                    "utf-8"
                ).strip()
                _logger.warning(clone_results_error_string)
                self.is_cloned = False
            else:
                self.is_cloned = True
        else:
            clone_cmd = ["git", "clone", "--depth", "1"]
            if self.branch_explicit and not self.commit_explicit:
                clone_cmd.extend(["-b", self.branch])
            if self.path_to_ssh_key:
                clone_cmd.extend(
                    [
                        "--config",
                        f"core.sshCommand=ssh -i {self.path_to_ssh_key}",
                    ]
                )
            clone_cmd.append(self.gitlink)
            clone_results = subprocess.run(clone_cmd)
            if clone_results.stderr:
                clone_results_error_string = clone_results.stderr.decode(
                    "utf-8"
                ).strip()
                _logger.warning(clone_results_error_string)
                self.is_cloned = False
            else:
                self.is_cloned = True

    def check_repo_url(self, repo_path: str, expected_url: str) -> bool:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        actual_url = result.stdout.strip()

        # Нормализация URL (убираем .git и trailing slash)
        actual_url = actual_url.rstrip(".git").rstrip("/")
        expected_url = expected_url.rstrip(".git").rstrip("/")

        if actual_url == expected_url:
            return True
        else:
            return False

    def __bool__(self) -> bool:
        return self.is_true

    def _git_stash(self) -> None:
        subprocess.run(["git", "stash"], cwd=self.project_path, capture_output=True)

    def _git_pull(self) -> None:
        subprocess.run(["git", "pull"], cwd=self.project_path, capture_output=True)

    def _git_checkout_ref(self, ref: str) -> None:
        subprocess.run(
            ["git", "checkout", ref],
            cwd=self.project_path,
            capture_output=True,
        )

    def _git_fetch_ref(self, ref: str) -> None:
        verify = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=self.project_path,
            capture_output=True,
        )
        if verify.returncode == 0:
            return
        subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", ref],
            cwd=self.project_path,
            capture_output=False,
        )

    def _checkout_version_branch(self, odoo_version: str) -> None:
        self.ensure_branch_exists(odoo_version, odoo_version)
        branch_commit_bytes = subprocess.run(
            ["git", "rev-parse", "--verify", odoo_version],
            cwd=self.project_path,
            capture_output=True,
        )
        branch_commit_string = (
            branch_commit_bytes.stdout.decode("utf-8").strip()
            or branch_commit_bytes.stderr.decode("utf-8").strip()
        )
        if "fatal" in branch_commit_string:
            newest_version = self.get_odoo_latest_version()
            self._git_checkout_ref(str(newest_version))
            self._git_pull()
            newest_version = self.get_odoo_latest_version()
            if str(newest_version) == odoo_version:
                self._git_checkout_ref(str(newest_version))
            else:
                _logger.error(
                    f"Version {odoo_version} not exists in git repository {self.project_path}"
                )
                exit(1)
        else:
            self._git_checkout_ref(odoo_version)

    def checkout_parsed_or_version(self, odoo_version: str) -> None:
        if self.link_type == constants.GITLINK_TYPE_FILE:
            return
        if not os.path.exists(os.path.join(self.project_path, ".git")):
            return

        if self.commit_explicit:
            self._git_fetch_ref(self.commit)
            self._git_checkout_ref(self.commit)
        elif self.branch_explicit:
            self.ensure_branch_exists(self.branch, odoo_version)
            self._git_checkout_ref(self.branch)
        else:
            self._checkout_version_branch(odoo_version)

    def ensure_branch_exists(self, branch_name: str, odoo_version: str) -> None:
        current_branches_bytes = subprocess.run(
            ["git", "branch"], cwd=self.project_path, capture_output=True
        )
        current_branches_string = current_branches_bytes.stdout.decode("utf-8").strip()
        if branch_name in current_branches_string:
            return
        current_remote_branches_bytes = subprocess.run(
            ["git", "branch", "-a"], cwd=self.project_path, capture_output=True
        )
        current_remote_branches_string = current_remote_branches_bytes.stdout.decode(
            "utf-8"
        ).strip()
        if f"origin/{odoo_version}" in current_remote_branches_string:
            return
        subprocess.run(
            [
                "git",
                "fetch",
                "--depth",
                "1",
                "origin",
                f"{branch_name}:{branch_name}",
            ],
            cwd=self.project_path,
            capture_output=False,
        )

    def get_odoo_latest_version(self) -> float:
        all_remote_branches_bytes = subprocess.run(
            ["git", "branch", "-r"],
            cwd=self.project_path,
            capture_output=True,
        )
        all_remote_branches_string = all_remote_branches_bytes.stdout.decode(
            "utf-8"
        ).strip()
        list_of_versions = []
        for branch_name in all_remote_branches_string.split("\n"):
            try:
                branch_version = float(branch_name.split("/")[1])
                list_of_versions.append(branch_version)
            except ValueError:
                continue
        return sorted(list_of_versions)[-1]

    def checkout(
        self,
        branch: str,
        *,
        commit: str | None = None,
        hard: bool = False,
        clean: bool = False,
        update: bool = False,
        odoo_version: str | None = None,
        odoo_version_sync: bool = False,
    ) -> None:
        if hard:
            self._git_stash()
            subprocess.run(
                ["git", "clean", "-fd"], cwd=self.project_path, capture_output=True
            )
            self._git_pull()
            self._git_checkout_ref(commit or branch)
            return

        odoo_version = odoo_version or branch

        if clean:
            self._git_stash()

        if odoo_version_sync:
            self.checkout_parsed_or_version(odoo_version)

        if update:
            self._git_pull()

    def checkout_repository(
        self,
        odoo_version: str,
        *,
        clean_git_repos: bool = False,
        update_git_repos: bool = False,
    ) -> None:
        self.checkout(
            odoo_version,
            clean=clean_git_repos,
            update=update_git_repos,
            odoo_version=odoo_version,
            odoo_version_sync=True,
        )

    def switch_to_branch(self, branch_name: str) -> None:
        _logger.info(
            translations.get_translation(translations.SWITCHING_TO_BRANCH).format(
                PROJECT_NAME=self.project_string,
                BRANCH_NAME=branch_name,
            )
        )
        self.checkout(branch_name, hard=True)
