"""Extension registry API for odpm plugins (4.4+)."""

from .context import ExtensionHostContext
from .protocols import (
    ComposeFragmentPlugin,
    HookRunner,
    PrepareStepFactory,
    PrepareStepPlugin,
)
from .registry import (
    PrepareStepRegistration,
    clear_registered_prepare_steps,
    get_compose_fragment,
    get_prepare_steps,
    hookimpl,
    hookspec,
    iter_compose_fragments,
    load_entry_point_prepare_steps,
    plugin_manager,
    register_compose_fragment,
    register_prepare_step,
    reset_extension_registry_state,
)
from .specs import OdpmExtensionSpecs, PROJECT_NAME

__all__ = [
    "ComposeFragmentPlugin",
    "ExtensionHostContext",
    "HookRunner",
    "OdpmExtensionSpecs",
    "PrepareStepFactory",
    "PrepareStepPlugin",
    "PrepareStepRegistration",
    "PROJECT_NAME",
    "clear_registered_prepare_steps",
    "get_compose_fragment",
    "get_prepare_steps",
    "hookimpl",
    "hookspec",
    "iter_compose_fragments",
    "load_entry_point_prepare_steps",
    "plugin_manager",
    "register_compose_fragment",
    "register_prepare_step",
    "reset_extension_registry_state",
]
