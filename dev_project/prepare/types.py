"""Prepare-phase context and step definition types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..compose.generator import ComposeGenerator
from ..git.deps_lock_manager import DepsLockManager
from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..plan import PlanStep
from ..project_env.links import ProjectLinks
from ..project_env.templates import ProjectTemplates

if TYPE_CHECKING:
    from ..config import Config
    from ..extensions.context import ExtensionHostContext
    from ..project_env import CreateProjectEnvironment
    from ..protocols import SystemCheckerProtocol


@dataclass
class PrepareContext:
    config: Config
    project_env: CreateProjectEnvironment
    templates: ProjectTemplates
    compose_generator: ComposeGenerator
    links: ProjectLinks
    system_checker: SystemCheckerProtocol
    args: OdpmCliArgs
    host_ctx: HostProjectContext
    lock_manager: DepsLockManager | None = None

    def extension_host(self) -> ExtensionHostContext:
        from ..extensions.context import ExtensionHostContext

        return ExtensionHostContext.from_config(self.config)


@dataclass(frozen=True)
class PrepareStepDef:
    id: str
    description: str
    evaluate: Callable[[PrepareContext], PlanStep]
    execute: Callable[[PrepareContext], None]
