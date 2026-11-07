"""Factory for stack runtime engines (Compose-only in 4.8)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .compose import ComposeRuntimeBackend

if TYPE_CHECKING:
    from ..config import Config
    from ..host.context import HostProjectContext
    from ..project_env import CreateProjectEnvironment


def get_runtime_backend(
    *,
    host_ctx: HostProjectContext,
    config: Config,
    project_env: CreateProjectEnvironment,
) -> ComposeRuntimeBackend:
    """Always Compose in this version — no env / CLI switch."""
    return ComposeRuntimeBackend(
        host_ctx=host_ctx,
        config=config,
        project_env=project_env,
    )
