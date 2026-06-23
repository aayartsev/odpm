"""Extension registry API for odpm plugins (4.4+)."""

from .api import (
    EXTENSION_API_VERSION,
    SUPPORTED_EXTENSION_API_VERSIONS,
    assert_extension_api_compatible,
)
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
    get_hook_runner,
    get_prepare_steps,
    hookimpl,
    hookspec,
    iter_compose_fragments,
    load_entry_point_prepare_steps,
    load_hook_runners,
    plugin_manager,
    register_compose_fragment,
    register_hook_runner,
    register_prepare_step,
    reset_extension_registry_state,
)
from .specs import OdpmExtensionSpecs, PROJECT_NAME

__all__ = [
    "EXTENSION_API_VERSION",
    "SUPPORTED_EXTENSION_API_VERSIONS",
    "ComposeFragmentPlugin",
    "ExtensionHostContext",
    "HookRunner",
    "OdpmExtensionSpecs",
    "PrepareStepFactory",
    "PrepareStepPlugin",
    "PrepareStepRegistration",
    "PROJECT_NAME",
    "assert_extension_api_compatible",
    "clear_registered_prepare_steps",
    "get_compose_fragment",
    "get_hook_runner",
    "get_prepare_steps",
    "hookimpl",
    "hookspec",
    "iter_compose_fragments",
    "load_entry_point_prepare_steps",
    "load_hook_runners",
    "plugin_manager",
    "register_compose_fragment",
    "register_hook_runner",
    "register_prepare_step",
    "reset_extension_registry_state",
]
