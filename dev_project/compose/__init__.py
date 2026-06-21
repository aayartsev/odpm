"""Docker Compose service spec, file generation, and runtime helpers."""

from .command_render import (
    render_compose_command_block,
    render_odpm_config_path_env_line,
    yaml_scalar,
)
from .start_command import ComposeOdooService, StartCommand

__all__ = [
    "COMPOSE_ODOO_SERVICE",
    "COMPOSE_STACK_SERVICES",
    "ComposeGenerator",
    "ComposeOdooService",
    "ComposeServiceBuilder",
    "StartCommand",
    "compose_stack_is_healthy",
    "container_is_running_and_healthy",
    "render_compose_command_block",
    "render_odpm_config_path_env_line",
    "should_force_recreate_compose",
    "yaml_scalar",
]


def __getattr__(name: str):
    if name == "ComposeGenerator":
        from .generator import ComposeGenerator

        return ComposeGenerator
    if name == "ComposeServiceBuilder":
        from .service_builder import ComposeServiceBuilder

        return ComposeServiceBuilder
    if name in (
        "COMPOSE_ODOO_SERVICE",
        "COMPOSE_STACK_SERVICES",
        "compose_stack_services",
        "compose_stack_is_healthy",
        "container_is_running_and_healthy",
        "should_force_recreate_compose",
    ):
        from . import runtime as runtime_module

        return getattr(runtime_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
