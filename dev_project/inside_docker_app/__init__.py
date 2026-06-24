"""In-container Odoo bootstrap, virtualenv checks, and entrypoints."""

import importlib

_INSIDE_DOCKER_APP_SUBMODULES = frozenset(
    {
        "check_odoo",
        "check_virtualenv",
        "container_bootstrap",
        "extras_sync",
        "logger",
        "odoo_checker",
        "params",
        "run_odoo",
        "run_pre_commit",
        "run_with_pydevd",
        "utils",
        "venv_import_smoke",
    }
)


def __getattr__(name: str):
    if name in _INSIDE_DOCKER_APP_SUBMODULES:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
