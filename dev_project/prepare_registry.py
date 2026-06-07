"""Backward-compatible shim for ``dev_project.prepare``."""

from __future__ import annotations

from .compose.service_builder import ComposeServiceBuilder
from .git.deps_lock_manager import DepsLockManager
from .plan_compose_preview import (
    compose_generate_needs_execute,
    compose_service_needs_update,
    vscode_settings_up_to_date,
)
from .plan_compose_runtime import compose_up_would_run, evaluate_compose_up_plan
from .prepare import (
    PREPARE_STEPS,
    PrepareContext,
    PrepareStepDef,
    build_plan,
    build_prepare_plan,
    build_runtime_plan_steps,
    build_runtime_plan_warnings,
    collect_execute_step_ids,
    collect_prepare_step_ids,
    collect_prepare_warnings,
    evaluate_prepare_plan,
    evaluate_prepare_step,
    execute_prepare,
    make_prepare_context,
    validate_prepare_context,
)
from .prepare.steps_compose import (
    evaluate_compose_generate as _evaluate_compose_generate,
    evaluate_compose_service as _evaluate_compose_service,
)

__all__ = (
    "PREPARE_STEPS",
    "ComposeServiceBuilder",
    "DepsLockManager",
    "PrepareContext",
    "PrepareStepDef",
    "build_plan",
    "build_prepare_plan",
    "build_runtime_plan_steps",
    "build_runtime_plan_warnings",
    "collect_execute_step_ids",
    "collect_prepare_step_ids",
    "collect_prepare_warnings",
    "compose_generate_needs_execute",
    "compose_service_needs_update",
    "compose_up_would_run",
    "evaluate_compose_up_plan",
    "evaluate_prepare_plan",
    "evaluate_prepare_step",
    "execute_prepare",
    "make_prepare_context",
    "validate_prepare_context",
    "vscode_settings_up_to_date",
    "_evaluate_compose_generate",
    "_evaluate_compose_service",
)
