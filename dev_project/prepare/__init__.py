"""Prepare-phase registry and execution for odpm plan and materializer.

Leaf types load eagerly. ``execute`` / ``registry`` load lazily so
``extensions.registry`` can import :class:`PrepareStepDef` without a cycle
through compose fragments.
"""

from __future__ import annotations

from typing import Any

from .types import PrepareContext, PrepareStepDef

__all__ = (
    "BUILTIN_PREPARE_STEPS",
    "PREPARE_STEPS",
    "PrepareContext",
    "PrepareStepDef",
    "get_prepare_steps",
    "build_plan",
    "build_prepare_plan",
    "build_runtime_plan_steps",
    "build_runtime_plan_warnings",
    "collect_execute_step_ids",
    "collect_prepare_step_ids",
    "collect_prepare_warnings",
    "evaluate_prepare_plan",
    "evaluate_prepare_step",
    "execute_prepare",
    "make_prepare_context",
    "validate_prepare_context",
)

_EXECUTE_EXPORTS = frozenset(
    {
        "build_plan",
        "build_prepare_plan",
        "build_runtime_plan_steps",
        "build_runtime_plan_warnings",
        "collect_execute_step_ids",
        "collect_prepare_step_ids",
        "collect_prepare_warnings",
        "evaluate_prepare_plan",
        "evaluate_prepare_step",
        "execute_prepare",
        "make_prepare_context",
        "validate_prepare_context",
    }
)

_REGISTRY_EXPORTS = frozenset(
    {
        "BUILTIN_PREPARE_STEPS",
        "PREPARE_STEPS",
        "get_prepare_steps",
    }
)


def __getattr__(name: str) -> Any:
    if name in _EXECUTE_EXPORTS:
        from . import execute as _execute  # noqa: PLC0415  # cycle

        value = getattr(_execute, name)
        globals()[name] = value
        return value
    if name in _REGISTRY_EXPORTS:
        from . import registry as _registry  # noqa: PLC0415  # cycle

        value = getattr(_registry, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
