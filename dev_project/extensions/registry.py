"""Extension registry: prepare steps, compose fragments, pluggy entry points."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import pluggy

from ..prepare.types import PrepareStepDef
from .protocols import ComposeFragmentPlugin, HookRunner, PrepareStepPlugin
from .specs import OdpmExtensionSpecs, PROJECT_NAME, hookimpl, hookspec

__all__ = [
    "PrepareStepRegistration",
    "clear_registered_prepare_steps",
    "get_compose_fragment",
    "get_hook_runner",
    "get_prepare_steps",
    "hookimpl",
    "hookspec",
    "iter_compose_fragments",
    "load_hook_runners",
    "load_entry_point_prepare_steps",
    "plugin_manager",
    "register_compose_fragment",
    "register_hook_runner",
    "register_prepare_step",
    "reset_extension_registry_state",
]

plugin_manager = pluggy.PluginManager(PROJECT_NAME)
plugin_manager.add_hookspecs(OdpmExtensionSpecs)

_MANUAL_PREPARE_STEPS: list[PrepareStepRegistration] = []
_COMPOSE_FRAGMENTS: dict[str, ComposeFragmentPlugin] = {}
_HOOK_RUNNERS: dict[str, HookRunner] = {}
_ENTRY_POINTS_LOADED = False
_HOOK_ENTRY_POINTS_LOADED = False


@dataclass(frozen=True)
class PrepareStepRegistration:
    plugin: PrepareStepPlugin
    order: int


@dataclass(frozen=True)
class _DataclassPrepareStepPlugin:
    id: str
    description: str
    evaluate: Any
    execute: Any
    order: int = 1000


def register_prepare_step(
    plugin: PrepareStepPlugin,
    *,
    order: int | None = None,
) -> None:
    """Register a prepare step programmatically (tests and built-in optional steps)."""
    step_order = order if order is not None else getattr(plugin, "order", 1000)
    registration = PrepareStepRegistration(plugin=plugin, order=step_order)
    if any(item.plugin.id == plugin.id for item in _MANUAL_PREPARE_STEPS):
        raise ValueError(f"duplicate prepare step id: {plugin.id!r}")
    _MANUAL_PREPARE_STEPS.append(registration)


def clear_registered_prepare_steps() -> None:
    """Reset manual prepare-step registrations (tests only)."""
    _MANUAL_PREPARE_STEPS.clear()


def reset_extension_registry_state() -> None:
    """Reset manual steps and pluggy plugins (tests only)."""
    global _ENTRY_POINTS_LOADED, _HOOK_ENTRY_POINTS_LOADED
    from .local import reset_local_plugins_state

    clear_registered_prepare_steps()
    _COMPOSE_FRAGMENTS.clear()
    _HOOK_RUNNERS.clear()
    reset_local_plugins_state()
    for _name, plugin in list(plugin_manager.list_name_plugin()):
        plugin_manager.unregister(plugin=plugin)
    _ENTRY_POINTS_LOADED = False
    _HOOK_ENTRY_POINTS_LOADED = False


def ensure_project_extensions_loaded(
    project_dir: str,
    *,
    manifest_extensions: object | None = None,
) -> None:
    """Load setuptools entry points and project-local plugins once per project."""
    from .local import load_project_local_plugins, local_allow_list_from_manifest

    load_hook_runners()
    _ensure_entry_points_loaded()
    allow_list = local_allow_list_from_manifest(manifest_extensions)
    load_project_local_plugins(project_dir, allow_list=allow_list)


def register_compose_fragment(name: str, plugin: ComposeFragmentPlugin) -> None:
    """Register a compose service fragment provider."""
    if name in _COMPOSE_FRAGMENTS:
        raise ValueError(f"duplicate compose fragment name: {name!r}")
    _COMPOSE_FRAGMENTS[name] = plugin


def get_compose_fragment(name: str) -> ComposeFragmentPlugin | None:
    return _COMPOSE_FRAGMENTS.get(name)


def iter_compose_fragments() -> tuple[tuple[str, ComposeFragmentPlugin], ...]:
    return tuple(sorted(_COMPOSE_FRAGMENTS.items()))


def register_hook_runner(name: str, runner: HookRunner) -> None:
    """Register a lifecycle hook runner by manifest plugin id."""
    if name in _HOOK_RUNNERS:
        raise ValueError(f"duplicate hook runner name: {name!r}")
    _HOOK_RUNNERS[name] = runner


def get_hook_runner(name: str) -> HookRunner | None:
    return _HOOK_RUNNERS.get(name)


def _coerce_hook_runner(item: Any) -> HookRunner | None:
    if item is None:
        return None
    if hasattr(item, "name") and (
        hasattr(item, "run_post_clone")
        or hasattr(item, "run_post_prepare")
        or hasattr(item, "run_pre_up")
    ):
        return item  # type: ignore[return-value]
    if callable(item):
        return _coerce_hook_runner(item())
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        return None
    return None


def _flatten_hook_runner_results(results: Iterable[Any]) -> list[HookRunner]:
    runners: list[HookRunner] = []
    for result in results:
        if result is None:
            continue
        if isinstance(result, Sequence) and not isinstance(result, (str, bytes)):
            for item in result:
                runner = _coerce_hook_runner(item)
                if runner is not None:
                    runners.append(runner)
            continue
        runner = _coerce_hook_runner(result)
        if runner is not None:
            runners.append(runner)
    return runners


def _ensure_hook_entry_points_loaded() -> None:
    global _HOOK_ENTRY_POINTS_LOADED
    if _HOOK_ENTRY_POINTS_LOADED:
        return
    plugin_manager.load_setuptools_entrypoints("odpm.hooks")
    _HOOK_ENTRY_POINTS_LOADED = True


def load_hook_runners() -> None:
    """Load third-party hook runners from pluggy entry points."""
    _ensure_hook_entry_points_loaded()
    hook_results = plugin_manager.hook.odpm_hook_runners()
    for runner in _flatten_hook_runner_results(hook_results):
        name = str(getattr(runner, "name", "")).strip()
        if not name:
            raise ValueError("hook runner plugin must define non-empty name")
        if name not in _HOOK_RUNNERS:
            register_hook_runner(name, runner)


def _coerce_prepare_step_plugin(item: Any) -> PrepareStepPlugin | None:
    if item is None:
        return None
    if isinstance(item, PrepareStepDef):
        return _DataclassPrepareStepPlugin(
            id=item.id,
            description=item.description,
            evaluate=item.evaluate,
            execute=item.execute,
            order=1000,
        )
    if isinstance(item, _DataclassPrepareStepPlugin):
        return item
    if (
        hasattr(item, "id")
        and hasattr(item, "evaluate")
        and hasattr(item, "execute")
    ):
        return item  # type: ignore[return-value]
    if callable(item):
        return _coerce_prepare_step_plugin(item())
    if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
        return None
    return None


def _flatten_prepare_step_results(results: Iterable[Any]) -> list[PrepareStepPlugin]:
    plugins: list[PrepareStepPlugin] = []
    for result in results:
        if result is None:
            continue
        if isinstance(result, Sequence) and not isinstance(result, (str, bytes)):
            for item in result:
                plugin = _coerce_prepare_step_plugin(item)
                if plugin is not None:
                    plugins.append(plugin)
            continue
        plugin = _coerce_prepare_step_plugin(result)
        if plugin is not None:
            plugins.append(plugin)
    return plugins


def _ensure_entry_points_loaded() -> None:
    global _ENTRY_POINTS_LOADED
    if _ENTRY_POINTS_LOADED:
        return
    plugin_manager.load_setuptools_entrypoints("odpm.prepare_steps")
    _ENTRY_POINTS_LOADED = True


def load_entry_point_prepare_steps() -> tuple[PrepareStepDef, ...]:
    """Load third-party prepare steps from pluggy entry points."""
    _ensure_entry_points_loaded()
    hook_results = plugin_manager.hook.odpm_prepare_steps()
    plugins = _flatten_prepare_step_results(hook_results)
    registrations = [
        PrepareStepRegistration(
            plugin=plugin,
            order=getattr(plugin, "order", 1000),
        )
        for plugin in plugins
    ]
    registrations.extend(_MANUAL_PREPARE_STEPS)
    registrations.sort(key=lambda item: (item.order, item.plugin.id))
    return tuple(_plugin_to_step_def(item.plugin) for item in registrations)


def get_prepare_steps(
    builtin_steps: tuple[PrepareStepDef, ...],
) -> tuple[PrepareStepDef, ...]:
    """Built-in prepare steps followed by extension steps sorted by ``order``."""
    extension_steps = load_entry_point_prepare_steps()
    return _merge_prepare_steps(builtin_steps, extension_steps)


def _plugin_to_step_def(plugin: PrepareStepPlugin) -> PrepareStepDef:
    return PrepareStepDef(
        plugin.id,
        plugin.description,
        plugin.evaluate,
        plugin.execute,
    )


def _merge_prepare_steps(
    builtin_steps: tuple[PrepareStepDef, ...],
    extension_steps: tuple[PrepareStepDef, ...],
) -> tuple[PrepareStepDef, ...]:
    if not extension_steps:
        return builtin_steps
    builtin_ids = {step.id for step in builtin_steps}
    for step in extension_steps:
        if step.id in builtin_ids:
            raise ValueError(
                f"extension prepare step id conflicts with built-in step: {step.id!r}"
            )
    return builtin_steps + extension_steps
