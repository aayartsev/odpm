"""Resolve odpm ``program_dir`` for legacy copy vs pip-installed layouts."""

from __future__ import annotations

from pathlib import Path

from . import constants
import dev_project

def resolve_program_dir(explicit: str | None = None) -> str:
    """Return the directory whose ``dev_project/`` subtree holds odpm templates.

    Legacy layout (repository copy)::

        program_dir/odpm.py
        program_dir/dev_project/templates/...

    Pip layout (``dev_project`` package under site-packages)::

        site-packages/dev_project/templates/...
        program_dir == site-packages (parent of the package directory)
    """
    if explicit is not None:
        explicit_path = Path(explicit).resolve()
        if (explicit_path / constants.DEV_PROJECT_DIR).is_dir():
            return str(explicit_path)

    package_dir = Path(dev_project.__file__).resolve().parent
    parent_dir = package_dir.parent
    return str(parent_dir)
