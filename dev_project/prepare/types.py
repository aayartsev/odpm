"""Prepare-phase context and step definition types."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..git.deps_lock_manager import DepsLockManager
from ..host_cli.args import OdpmCliArgs
from ..host_context import HostProjectContext
from ..plan import PlanStep

if TYPE_CHECKING:
    from ..config import Config
    from ..project_env import CreateProjectEnvironment
    from ..protocols import SystemCheckerProtocol


@dataclass
class PrepareContext:
    config: Config
    project_env: CreateProjectEnvironment
    system_checker: SystemCheckerProtocol
    args: OdpmCliArgs
    host_ctx: HostProjectContext
    lock_manager: DepsLockManager | None = None


@dataclass(frozen=True)
class PrepareStepDef:
    id: str
    description: str
    evaluate: Callable[[PrepareContext], PlanStep]
    execute: Callable[[PrepareContext], None]
