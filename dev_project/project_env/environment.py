from ..git import HandleOdooProjectLink
from ..config import Config
from ..errors import PipelineError
from ..protocols import RuntimeProjectServicesProtocol, SystemCheckerProtocol
from ..dependency_resolver import DependencyResolutionResult
from .base_image import BaseImageBuilder
from ..compose.generator import ComposeGenerator
from .links import ProjectLinks
from .services import CiImageBuildService, PlatformSourcesService, VscodeConfigurator
from .templates import ProjectTemplates
from .types import MappedPath, SymlinksSources


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
        self._ci_build = CiImageBuildService(self)
        self._links = ProjectLinks(self)
        self._base_image = BaseImageBuilder(self)
        self._platform_sources = PlatformSourcesService(self)
        self._vscode = VscodeConfigurator(self)

    def attach_system_checker(self, checker: SystemCheckerProtocol) -> None:
        self._system_checker = checker

    def _require_system_checker(self) -> SystemCheckerProtocol:
        if self._system_checker is None:
            raise PipelineError(
                "System checker is not attached to CreateProjectEnvironment"
            )
        return self._system_checker

    def generate_vscode_settings_json(self) -> None:
        self._vscode.generate_vscode_settings_json()

    def prepare_ci_build_context(self) -> None:
        self._ci_build.prepare_ci_build_context()

    def generate_ci_dockerfile(self) -> str:
        return self._ci_build.generate_ci_dockerfile()

    def build_ci_image(self) -> None:
        self._ci_build.build_ci_image()

    def _resolve_dependencies(self) -> DependencyResolutionResult:
        return self._links._resolve_dependencies()

    def _read_ci_dockerignore_template(self) -> str:
        return self._ci_build.read_ci_dockerignore_template()

    def _build_ci_venv_install_spec(self):
        return self._ci_build.build_ci_venv_install_spec()

    def get_vscode_dir_path(self) -> str:
        return self._vscode.get_vscode_dir_path()

    def update_vscode_debugger_launcher(self) -> None:
        self._vscode.update_vscode_debugger_launcher()

    def download_odoo_repository(self) -> None:
        self._platform_sources.download_odoo_repository()

    def download_odoo_nightly_build(self) -> None:
        self._platform_sources.download_odoo_nightly_build()

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
