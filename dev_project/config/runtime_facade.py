"""Runtime facade properties for :class:`~dev_project.config.config.Config`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..host.runtime import HostRuntimeState
from ..start_command import ComposeOdooService

if TYPE_CHECKING:
    from .config import Config


class ConfigRuntimeFacadeMixin:
    @property
    def runtime(self: Config) -> HostRuntimeState:
        if not hasattr(self, "_runtime"):
            self._runtime = HostRuntimeState()
        return self._runtime

    @property
    def compose_service(self: Config) -> ComposeOdooService | None:
        return self.runtime.compose_service

    @compose_service.setter
    def compose_service(self: Config, value: ComposeOdooService | None) -> None:
        self.runtime.compose_service = value

    @property
    def container_run_mode(self: Config) -> str:
        return self.runtime.container_run_mode

    @container_run_mode.setter
    def container_run_mode(self: Config, value: str) -> None:
        self.runtime.container_run_mode = value

    @property
    def no_log_prefix(self: Config) -> bool:
        return self.runtime.no_log_prefix

    @no_log_prefix.setter
    def no_log_prefix(self: Config, value: bool) -> None:
        self.runtime.no_log_prefix = value

    @property
    def docker_compose_command(self: Config) -> str:
        return self.runtime.resolved_docker_compose_command(
            self._docker.docker_compose_command
        )

    @docker_compose_command.setter
    def docker_compose_command(self: Config, value: str) -> None:
        self.runtime.docker_compose_command = value
