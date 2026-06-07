from ..git import HandleOdooProjectLink
from ..config import Config
from ..errors import PipelineError
from ..protocols import SystemCheckerProtocol
from ..compose.generator import ComposeGenerator
from .links import ProjectLinks
from .templates import ProjectTemplates
from .types import MappedPath, SymlinksSources


class CreateProjectEnvironment:
    """Prepare wiring and shared project state (mapped_folders, links, templates)."""

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
        self._links = ProjectLinks(self)

    def attach_system_checker(self, checker: SystemCheckerProtocol) -> None:
        self._system_checker = checker

    def _require_system_checker(self) -> SystemCheckerProtocol:
        if self._system_checker is None:
            raise PipelineError(
                "System checker is not attached to CreateProjectEnvironment"
            )
        return self._system_checker

    @property
    def templates(self) -> ProjectTemplates:
        return self._templates

    @property
    def compose_generator(self) -> ComposeGenerator:
        return self._compose

    @property
    def links(self) -> ProjectLinks:
        return self._links
