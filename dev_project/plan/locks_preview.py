"""Git lock source and manifest ↔ deps.lock divergence plan warnings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..git.deps_lock import deps_lock_path, load_deps_lock
from ..host.context import HostProjectContext
from ..manifest.locks import (
    LockSource,
    compare_manifest_and_deps_git_locks,
    manifest_git_locks_from_view,
    resolve_lock_source_from_view,
)
from ..translations import _
from .core import deps_lock_file_exists

if TYPE_CHECKING:
    from ..manifest.reader import ManifestView


def collect_git_lock_warnings(
    host_ctx: HostProjectContext,
    manifest_view: ManifestView | None = None,
) -> tuple[str, ...]:
    """Warnings about lock source and manifest vs deps.lock drift."""
    project_dir = host_ctx.project_dir
    warnings: list[str] = []
    source = resolve_lock_source_from_view(manifest_view)

    if source == LockSource.MANIFEST:
        warnings.append(
            _(
                "Git lock source: manifest locks.git in odpm.json (canonical); "
                "edit SHA in locks.git and run --update-lock to sync "
                ".odpm/deps.lock.json."
            )
        )
    elif deps_lock_file_exists(project_dir):
        warnings.append(
            _(
                "Git lock source: .odpm/deps.lock.json; run --update-lock after "
                "changing dependencies."
            )
        )

    if source != LockSource.MANIFEST or not deps_lock_file_exists(project_dir):
        return tuple(warnings)

    try:
        file_lock = load_deps_lock(deps_lock_path(project_dir))
    except ValueError:
        return tuple(warnings)

    divergences = compare_manifest_and_deps_git_locks(
        manifest_git_locks_from_view(manifest_view),
        file_lock,
    )
    for detail in divergences:
        warnings.append(
            _("manifest locks.git vs deps.lock.json differ: {DETAIL}").format(
                DETAIL=detail
            )
        )
    if divergences:
        warnings.append(
            _(
                "Canonical git pins: odpm.json locks.git; run --update-lock to "
                "refresh .odpm/deps.lock.json."
            )
        )
    return tuple(warnings)
