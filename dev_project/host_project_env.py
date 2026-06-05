import json
import os
import subprocess
import sys
from pathlib import Path

from . import constants, translations
from .ci_image_builder import CiImageBuilder
from .compose_generator import ComposeGenerator
from .handle_odoo_project_git_link import HandleOdooProjectLink
from .host_config import Config
from .inside_docker_app.logger import get_module_logger
from .inside_docker_app.utils import (
    delete_files_in_directory,
    download_file,
    un_zip_file_to_directory,
)
from .project_env_types import (
    DebuggerPathRecord,
    DebuggerUnit,
    MappedPath,
    MappedSources,
    SymlinksSources,
)
from .project_links import ProjectLinks
from .project_templates import ProjectTemplates
from .protocols import CreateProjectEnvironmentProtocol

_logger = get_module_logger(__name__)

__all__ = [
    "CreateProjectEnvironment",
    "MappedPath",
    "MappedSources",
    "SymlinksSources",
    "DebuggerPathRecord",
    "DebuggerUnit",
]


class CreateProjectEnvironment(CreateProjectEnvironmentProtocol):
    def __init__(self, config: Config):
        self.config = config
        self.user_env = self.config.user_env
        self.config.project_env = self
        self.odoo_platform_project: HandleOdooProjectLink
        self.mapped_folders: list[MappedPath] = []
        self._templates = ProjectTemplates(self)
        self._compose = ComposeGenerator(self)
        self._ci = CiImageBuilder(self)
        self._links = ProjectLinks(self)

    def map_folders(self) -> None:
        self._links.map_folders()

    def generate_dockerfile(self) -> None:
        self._templates.generate_dockerfile()

    def generate_dockerignore(self) -> None:
        self._templates.generate_dockerignore()

    def generate_config_file(self) -> None:
        self._templates.generate_config_file()

    def generate_docker_compose_file(self) -> None:
        self._compose.generate_docker_compose_file()

    def checkout_dependencies(self) -> None:
        self._links.checkout_dependencies()

    def checkout_project(self, project: HandleOdooProjectLink) -> None:
        self._links.checkout_project(project)

    def update_links(self) -> None:
        self._links.update_links()

    def generate_vscode_settings_json(self) -> None:
        self._templates.generate_vscode_settings_json()

    def prepare_ci_build_context(self) -> None:
        self._ci.prepare_ci_build_context()

    def generate_ci_dockerfile(self) -> str:
        return self._ci.generate_ci_dockerfile()

    def build_ci_image(self) -> None:
        self._ci.build_ci_image()

    def _resolve_dependencies(self) -> list[str]:
        return self._links._resolve_dependencies()

    def _read_ci_dockerignore_template(self) -> str:
        return self._ci._read_ci_dockerignore_template()

    def _build_ci_venv_install_spec(self):
        return self._ci._build_ci_venv_install_spec()

    def get_vscode_dir_path(self) -> str:
        vscode_dir = os.path.join(self.config.project_dir, ".vscode")
        if not os.path.exists(vscode_dir):
            os.mkdir(vscode_dir)
        return vscode_dir

    def update_vscode_debugger_launcher(self) -> None:
        def get_list_of_mapped_sources() -> None:
            list_for_links = [
                symlink_item for symlink_item in self.config.symlinks_sources
            ]
            for linking_dir in list_for_links:
                dir_name_to_link = os.path.basename(linking_dir.link_path)
                for mapped_folder in self.mapped_folders:
                    mapped_dir_name = os.path.basename(mapped_folder.local)
                    if (
                        dir_name_to_link == mapped_dir_name
                        and linking_dir.source_path not in [self.user_env.backups]
                    ):
                        self.config.debugger_path_mappings.append(
                            DebuggerPathRecord(
                                localRoot=linking_dir.link_path,
                                remoteRoot=mapped_folder.docker,
                            )
                        )

        launch_json = os.path.join(self.get_vscode_dir_path(), "launch.json")
        if not os.path.exists(launch_json):
            content = {"configurations": []}
        else:
            with open(launch_json, "r") as open_file:
                content = json.load(open_file)
        debugger_unit_exists = False
        get_list_of_mapped_sources()
        port = self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT
        odoo_debugger_uint = DebuggerUnit(
            name=constants.DEBUGGER_UNIT_NAME,
            type="python",
            request="attach",
            port=int(port),
            host="localhost",
            pathMappings=self.config.debugger_path_mappings,
        )
        for index, debugger_unit in enumerate(content["configurations"]):
            if debugger_unit["name"] == constants.DEBUGGER_UNIT_NAME:
                content["configurations"][index] = odoo_debugger_uint
                debugger_unit_exists = True
        if not debugger_unit_exists:
            content["configurations"].append(
                DebuggerUnit(
                    name=constants.DEBUGGER_UNIT_NAME,
                    type="python",
                    request="attach",
                    port=self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT,
                    host="localhost",
                    pathMappings=self.config.debugger_path_mappings,
                )
            )
        with open(launch_json, "w") as outfile:
            json.dump(content, outfile, indent=4)

    def download_odoo_repository(self):
        self.config.system_checker.check_free_space_for_odoo_developing()
        dir_for_odoo_src = os.path.join(self.config.odoo_src_dir, "..")
        os.chdir(dir_for_odoo_src)
        delete_files_in_directory(self.config.odoo_src_dir)
        subprocess.run(["git", "clone", "--depth", "1", constants.ODOO_GIT_LINK])

    def download_odoo_nightly_build(self):
        self.config.system_checker.check_free_space_for_odoo_developing(
            free_space_size=2.0
        )
        dir_for_odoo_src = os.path.join(self.config.odoo_src_dir, "..")
        os.chdir(dir_for_odoo_src)
        delete_files_in_directory(self.config.odoo_src_dir)
        odoo_version = self.config.odoo_version
        odoo_build_date = (
            self.config.odoo_build_date or constants.ODOO_DEFAULT_BUILD_DATE
        )
        link_to_download = f"https://nightly.odoo.com/{odoo_version}/nightly/src/odoo_{odoo_version}.{odoo_build_date}.zip"
        filepath_to_save = os.path.join(Path.home(), "odoo.zip.download")
        download_file(
            link_to_download=link_to_download,
            filepath_to_save=filepath_to_save,
        )
        un_zip_file_to_directory(
            dir_for_odoo_src,
            filepath_to_save,
            rename_first_part_of_path="odoo",
        )
        os.replace(
            os.path.join(self.config.odoo_src_dir, "setup", "odoo"),
            os.path.join(self.config.odoo_src_dir, "odoo-bin"),
        )
        if os.path.exists(filepath_to_save):
            os.remove(filepath_to_save)

    def base_image_exists(self) -> bool:
        process_result = subprocess.run(
            ["docker", "images", "--format", "'{{json .}}'"], capture_output=True
        )
        output_string = process_result.stdout.decode("utf-8")
        for record in output_string.split("\n"):
            if not record:
                continue
            new_record = json.loads(record.replace("'", ""))
            if self.config.odoo_image_name == new_record.get("Repository"):
                return True
        return False

    def ensure_base_image(self) -> None:
        if not self.base_image_exists():
            self.build_base_image()

    def build_base_image(self) -> None:
        os.chdir(self.config.project_dir)
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                self.config.dockerfile_path,
                "-t",
                self.config.odoo_image_name,
                f"--platform=linux/{self.config.arch}",
                self.config.project_dir,
            ]
        )
