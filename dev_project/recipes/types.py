"""Shared types for odpm recipes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RecipeParam:
    name: str
    required: bool = False
    env: str | None = None
    description: str = ""


@dataclass(frozen=True)
class OdpmStep:
    """One odpm argv invocation (without the odpm binary prefix)."""

    argv: tuple[str, ...]
    capture: bool = False
    timeout: float | None = 120.0
    # When True, runner still executes this step under --dry-run (e.g. modules diff).
    execute_even_if_dry_run: bool = False
    label: str = ""


@dataclass(frozen=True)
class StepResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    skipped: bool = False


@dataclass
class RecipeContext:
    project_dir: str
    program_dir: str
    params: dict[str, str]
    environ: dict[str, str]
    dry_run: bool = False
    scratch: dict[str, Any] = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)
    planned_argv: list[list[str]] = field(default_factory=list)
