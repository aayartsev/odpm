"""Load project-local extension plugins from ``.odpm/plugins/``."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _

_logger = get_module_logger(__name__)

LOCAL_PLUGINS_DIRNAME = "plugins"
_LOADED_PROJECT_DIRS: set[str] = set()


def reset_local_plugins_state() -> None:
    """Clear per-project load cache (tests only)."""
    _LOADED_PROJECT_DIRS.clear()


def _plugins_root(project_dir: str) -> Path:
    root = Path(project_dir).resolve()
    return root / ".odpm" / LOCAL_PLUGINS_DIRNAME


def _resolve_plugin_module_path(plugins_root: Path, module_name: str) -> Path:
    if not module_name or module_name.startswith(".") or "/" in module_name or "\\" in module_name:
        raise ConfigError(
            _("Invalid local plugin module name: {NAME!r}").format(NAME=module_name)
        )
    candidate = (plugins_root / f"{module_name}.py").resolve()
    try:
        candidate.relative_to(plugins_root.resolve())
    except ValueError as exc:
        raise ConfigError(
            _("Local plugin path escapes .odpm/plugins: {NAME!r}").format(NAME=module_name)
        ) from exc
    return candidate


def _import_plugin_module(module_path: Path, *, module_name: str) -> None:
    if not module_path.is_file():
        raise ConfigError(
            _("Local plugin module not found: {PATH}").format(PATH=module_path)
        )
    qualified = f"odpm_local_plugin_{module_name}"
    spec = importlib.util.spec_from_file_location(qualified, module_path)
    if spec is None or spec.loader is None:
        raise ConfigError(
            _("Cannot load local plugin module: {PATH}").format(PATH=module_path)
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)


def _discover_local_module_names(plugins_root: Path) -> tuple[str, ...]:
    if not plugins_root.is_dir():
        return ()
    return tuple(
        sorted(path.stem for path in plugins_root.glob("*.py") if path.is_file())
    )


def load_project_local_plugins(
    project_dir: str,
    *,
    allow_list: tuple[str, ...] | None = None,
) -> None:
    """Import local plugin modules under ``{project_dir}/.odpm/plugins``."""
    resolved_dir = str(Path(project_dir).resolve())
    if resolved_dir in _LOADED_PROJECT_DIRS:
        return
    plugins_root = _plugins_root(resolved_dir)
    if allow_list is not None:
        module_names = allow_list
    else:
        module_names = _discover_local_module_names(plugins_root)
    for module_name in module_names:
        module_path = _resolve_plugin_module_path(plugins_root, module_name)
        if not module_path.is_file():
            _logger.warning(
                "Skipping missing local plugin module %r (%s)",
                module_name,
                module_path,
            )
            continue
        _logger.info("Loading local odpm plugin %s", module_name)
        _import_plugin_module(module_path, module_name=module_name)
    _LOADED_PROJECT_DIRS.add(resolved_dir)


def local_allow_list_from_manifest(manifest_extensions: Any) -> tuple[str, ...] | None:
    if not isinstance(manifest_extensions, dict):
        return None
    raw = manifest_extensions.get("local")
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ConfigError(_("extensions.local must be a list of module names"))
    return tuple(str(item).strip() for item in raw if str(item).strip())
