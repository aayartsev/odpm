import os
import subprocess
from pathlib import Path

from .. import constants
from ..git import HandleOdooProjectLink
from ..config import Config
from ..inside_docker_app.utils import (
    delete_files_in_directory,
    download_file,
    un_zip_file_to_directory,
)
from ..protocols import CreateProjectEnvironmentProtocol
from .base_image import BaseImageBuilder
from .ci_image import CiImageBuilder
from .compose import ComposeGenerator
from .links import ProjectLinks
from .templates import ProjectTemplates
from .types import (
    DebuggerPathRecord,
    DebuggerUnit,
    MappedPath,
    SymlinksSources,
)


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
        self._base_image = BaseImageBuilder(self)

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
        return self._templates.get_vscode_dir_path()

    def update_vscode_debugger_launcher(self) -> None:
        self._templates.update_vscode_debugger_launcher()

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
        return self._base_image.base_image_exists()

    def ensure_base_image(self) -> None:
        self._base_image.ensure_base_image()

    def build_base_image(self) -> None:
        self._base_image.build_base_image()
