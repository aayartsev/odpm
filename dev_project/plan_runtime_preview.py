"""Backward-compatible shim for ``dev_project.plan.runtime_preview``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.plan.runtime_preview")


from dev_project.plan.runtime_preview import (
    PLAN_ONLY_ARGUMENT_KEYS,
    clear_runtime_config_preview_cache,
    format_runtime_config_payload,
    normalize_runtime_config_text,
    normalized_runtime_config_text_from_disk,
    prepare_runtime_config_for_compose_preview,
    preview_runtime_config_text,
    runtime_config_payload_from_config,
    strip_plan_only_arguments,
)

__all__ = [
    "PLAN_ONLY_ARGUMENT_KEYS",
    "clear_runtime_config_preview_cache",
    "format_runtime_config_payload",
    "normalize_runtime_config_text",
    "normalized_runtime_config_text_from_disk",
    "prepare_runtime_config_for_compose_preview",
    "preview_runtime_config_text",
    "runtime_config_payload_from_config",
    "strip_plan_only_arguments",
]
