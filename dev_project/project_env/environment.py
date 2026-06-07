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
from ..errors import PipelineError
from ..protocols import RuntimeProjectServicesProtocol, SystemCheckerProtocol
from ..dependency_resolver import DependencyResolutionResult
from .base_image import BaseImageBuilder
from .ci_image import CiImageBuilder
from ..compose.generator import ComposeGenerator
from .links import ProjectLinks
from .templates import ProjectTemplates
from .types import (
    DebuggerPathRecord,
    DebuggerUnit,
    MappedPath,
    SymlinksSources,
)


class CreateProjectEnvironment(RuntimeProjectServicesProtocol):
    def __init__(
        self,
        config: Config,
        *,
        system_checker: SystemCheckerProtocol | None = None,
    ) -> None:
        self.config = config
        self.user_env = self.config.user_env
        self.odoo_platform_project: HandleOdooProjectLink
        self.mapped_folders: list[MappedPath] = []
        self._system_checker = system_checker
        self._templates = ProjectTemplates(self)
        self._compose = ComposeGenerator(self)
        self._ci = CiImageBuilder(self)
        self._links = ProjectLinks(self)
        self._base_image = BaseImageBuilder(self)

    def attach_system_checker(self, checker: SystemCheckerProtocol) -> None:
        self._system_checker = checker

    def _require_system_checker(self) -> SystemCheckerProtocol:
        if self._system_checker is None:
            raise PipelineError(
                "System checker is not attached to CreateProjectEnvironment"
            )
        return self._system_checker

    def generate_vscode_settings_json(self) -> None:
        self._templates.generate_vscode_settings_json()

    def prepare_ci_build_context(self) -> None:
        self._ci.prepare_ci_build_context()

    def generate_ci_dockerfile(self) -> str:
        return self._ci.generate_ci_dockerfile()

    def build_ci_image(self) -> None:
        self._ci.build_ci_image()

    def _resolve_dependencies(self) -> DependencyResolutionResult:
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
        self._require_system_checker().check_free_space_for_odoo_developing()
        parent_dir = os.path.dirname(self.config.odoo_src_dir)
        delete_files_in_directory(self.config.odoo_src_dir)
        subprocess.run(
            ["git", "clone", "--depth", "1", constants.ODOO_GIT_LINK],
            cwd=parent_dir,
        )

    def download_odoo_nightly_build(self):
        self._require_system_checker().check_free_space_for_odoo_developing(
            free_space_size=2.0
        )
        parent_dir = os.path.dirname(self.config.odoo_src_dir)
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
            parent_dir,
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

    @property
    def templates(self) -> ProjectTemplates:
        return self._templates

    @property
    def compose_generator(self) -> ComposeGenerator:
        return self._compose

    @property
    def links(self) -> ProjectLinks:
        return self._links
