"""Materialize manifest ``service_sources`` into ``ODOO_PROJECTS_DIR/service-sources/<name>``.

With ``--git-worktree`` / ``ODPM_GIT_WORKTREE``, remote sources use ``mirrors/`` +
``worktrees/<tenant>/<repo-key>/`` instead of ``service-sources/<name>`` (ADR-028).
"""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from .. import constants
from ..errors import ConfigError, GitError
from ..logging import get_module_logger
from ..subprocess_runner import run_logged
from ..symlinks.manager import SymlinkManager
from ..translations import _
from .runner import GitRunner
from .worktree import (
    git_worktree_requested,
    is_git_work_tree,
    materialize_link_as_worktree,
    repo_key_from_relative_path,
    tenant_id_from_project_dir,
    worktree_path,
)

from ..host.ports import BootstrapHandle

if TYPE_CHECKING:
    from ..host.context import HostProjectContext
    from .deps_lock import LockEntry
from ..config.transforms.env_substitution import inject_service_source_paths
from ..manifest.reader import refresh_manifest_view_compose_expansion
from ..symlinks.repo import _symlink_host_view


_logger = get_module_logger(__name__)

SERVICE_SOURCES_DIR = constants.SERVICE_SOURCES_DIR


def service_source_target_dir(bootstrap: BootstrapHandle, name: str) -> str:
    """Absolute clone directory for a named service source (classic layout)."""

    host = bootstrap.host_context()
    return os.path.abspath(
        os.path.join(
            host.user_env.odoo_projects_dir,
            SERVICE_SOURCES_DIR,
            name,
        )
    )


def _service_source_worktree_dir(bootstrap: BootstrapHandle, project_link) -> str:

    host = bootstrap.host_context()
    tenant = tenant_id_from_project_dir(host.project_dir)
    repo_key = repo_key_from_relative_path(project_link.project_data.relative_path)
    return worktree_path(host.user_env.odoo_projects_dir, tenant, repo_key)


def resolve_file_service_source_path(git_link: str) -> str:
    local = git_link.strip().replace("file://", "").strip().rstrip("/")
    if not local:
        raise ConfigError(
            _("service_sources file:// link must be a non-empty path.")
        )
    return os.path.abspath(local)


def materialize_service_sources(
    bootstrap: BootstrapHandle,
    *,
    lock_entries: dict[str, LockEntry] | None = None,
) -> dict[str, str]:
    """Clone or update service sources; return name → absolute host path."""
    view = bootstrap.manifest_view
    sources = view.service_sources if view is not None else None
    if not sources:
        return {}

    paths: dict[str, str] = {}
    for name, git_link in sorted(sources.items()):
        lock_entry = (lock_entries or {}).get(name)
        paths[name] = materialize_one_service_source(
            bootstrap,
            name,
            git_link,
            lock_entry=lock_entry,
        )
    return paths


def materialize_one_service_source(
    bootstrap: BootstrapHandle,
    name: str,
    git_link: str,
    *,
    lock_entry: LockEntry | None = None,
) -> str:

    host = bootstrap.host_context()
    link = git_link.strip()
    if not link:
        raise ConfigError(
            _("service_sources.{NAME} must be a non-empty git link.").format(NAME=name)
        )

    if link.startswith("file://"):
        path = resolve_file_service_source_path(link)
        if not os.path.isdir(path):
            raise ConfigError(
                _(
                    "Service source {NAME} file:// path does not exist: {PATH}"
                ).format(NAME=name, PATH=path)
            )
        return path

    project_link = bootstrap.handle_git_link(link, materialize=False)
    if lock_entry is not None:
        from .deps_lock import apply_lock_entry_to_link  # noqa: PLC0415  # optional

        apply_lock_entry_to_link(project_link, lock_entry)

    if getattr(project_link, "worktree_mode", False) is True or (
        git_worktree_requested(host.arguments)
        and project_link.link_type
        in (
            constants.GITLINK_TYPE_HTTP,
            constants.GITLINK_TYPE_GIT,
            constants.GITLINK_TYPE_SSH,
        )
    ):
        if getattr(project_link, "worktree_mode", False) is not True:
            from .worktree import configure_link_worktree_context

            configure_link_worktree_context(
                project_link,
                tenant=tenant_id_from_project_dir(host.project_dir),
                skip_git_update=bootstrap.skip_git_update(),
            )
        target = materialize_link_as_worktree(
            project_link,
            odoo_version=str(host.project_settings.odoo_version),
        )
        if project_link.branch and not bootstrap.skip_git_update():
            project_link.checkout_repository(
                str(host.project_settings.odoo_version),
                clean_git_repos=host.user_settings.clean_git_repos,
                update_git_repos=host.user_settings.update_git_repos,
            )
            target = project_link.project_path
        if not os.path.isdir(target):
            raise ConfigError(
                _("Service source {NAME} materialize failed: {PATH}").format(
                    NAME=name,
                    PATH=target,
                )
            )
        _logger.info(
            _("Materialized service source {NAME} at {PATH}").format(
                NAME=name,
                PATH=target,
            )
        )
        return target

    base_root = os.path.join(host.user_env.odoo_projects_dir, SERVICE_SOURCES_DIR)
    os.makedirs(base_root, exist_ok=True)
    target = service_source_target_dir(bootstrap, name)

    git_dir = os.path.join(target, ".git")
    if os.path.isdir(git_dir):
        project_link.project_path = target
        project_link.dir_to_clone = base_root
        project_link.check_project()
    else:
        if os.path.exists(target):
            shutil.rmtree(target)
        _clone_service_source_repo(project_link, target_dir=target, base_root=base_root)

    if project_link.branch and not bootstrap.skip_git_update():
        project_link.checkout_repository(
            str(host.project_settings.odoo_version),
            clean_git_repos=host.user_settings.clean_git_repos,
            update_git_repos=host.user_settings.update_git_repos,
        )

    if not os.path.isdir(target):
        raise ConfigError(
            _("Service source {NAME} materialize failed: {PATH}").format(
                NAME=name,
                PATH=target,
            )
        )
    _logger.info(
        _("Materialized service source {NAME} at {PATH}").format(
            NAME=name,
            PATH=target,
        )
    )
    return target


def _clone_service_source_repo(
    project_link,
    *,
    target_dir: str,
    base_root: str,
) -> None:
    runner = GitRunner(project_link)
    clone_name = os.path.basename(target_dir)
    clone_args = ["clone", project_link.gitlink, clone_name]
    if project_link.branch_explicit and not project_link.commit_explicit:
        clone_args = ["clone", "-b", project_link.branch, project_link.gitlink, clone_name]

    returncode = run_logged(
        runner.build_git_cmd(clone_args),
        cwd=base_root,
    )
    if returncode != 0:
        message = (
            f"git clone failed for service source {project_link.gitlink!r} "
            f"(exit code {returncode})"
        )
        _logger.error(message)
        raise GitError(message)

    project_link.project_path = target_dir
    project_link.dir_to_clone = base_root
    project_link.is_cloned = True


def collect_service_source_paths(bootstrap: BootstrapHandle) -> dict[str, str]:
    """Resolve current on-disk paths for effective ``service_sources``."""

    host = bootstrap.host_context()
    view = bootstrap.manifest_view
    sources = view.service_sources if view is not None else None
    if not sources:
        return {}
    use_wt = git_worktree_requested(host.arguments)
    paths: dict[str, str] = {}
    for name, git_link in sources.items():
        link = git_link.strip()
        if link.startswith("file://"):
            paths[name] = resolve_file_service_source_path(link)
        elif use_wt:
            project_link = bootstrap.handle_git_link(link, materialize=False)
            paths[name] = _service_source_worktree_dir(bootstrap, project_link)
        else:
            paths[name] = service_source_target_dir(bootstrap, name)
    return paths


def ensure_service_sources_present(bootstrap: BootstrapHandle) -> None:
    if not service_sources_need_materialize(bootstrap):
        return
    missing = []
    for name, path in collect_service_source_paths(bootstrap).items():
        if not os.path.isdir(path):
            missing.append(f"{name}: {path}")
    if missing:
        raise ConfigError(
            _(
                "--no-git-update requires existing service_sources directories: "
                "{PATHS}"
            ).format(PATHS=", ".join(missing))
        )


def service_sources_need_materialize_for_view(
    *,
    manifest_view,
    odoo_projects_dir: str,
    use_worktree: bool = False,
    project_dir: str | None = None,
    path_to_ssh_key: str = "",
) -> bool:
    sources = manifest_view.service_sources if manifest_view is not None else None
    if not sources:
        return False
    for name, git_link in sources.items():
        link = git_link.strip()
        if link.startswith("file://"):
            path = resolve_file_service_source_path(link)
            if not os.path.isdir(path):
                return True
            continue
        if use_worktree and project_dir:
            from .link import HandleOdooProjectLink

            project_link = HandleOdooProjectLink(
                link,
                path_to_ssh_key,
                odoo_projects_dir,
                system_type="standart",
            )
            tenant = tenant_id_from_project_dir(project_dir)
            repo_key = repo_key_from_relative_path(
                project_link.project_data.relative_path
            )
            target = worktree_path(odoo_projects_dir, tenant, repo_key)
            if not is_git_work_tree(target):
                return True
            continue
        target = os.path.abspath(
            os.path.join(odoo_projects_dir, SERVICE_SOURCES_DIR, name)
        )
        if not is_git_work_tree(target):
            return True
    return False


def service_sources_need_materialize(bootstrap: BootstrapHandle) -> bool:

    host = bootstrap.host_context()
    view = bootstrap.manifest_view
    return service_sources_need_materialize_for_view(
        manifest_view=view,
        odoo_projects_dir=host.user_env.odoo_projects_dir,
        use_worktree=git_worktree_requested(host.arguments),
        project_dir=host.project_dir,
        path_to_ssh_key=host.user_env.path_to_ssh_key,
    )


def apply_materialized_service_sources(
    bootstrap: BootstrapHandle,
    source_paths: dict[str, str],
    *,
    host_ctx: HostProjectContext | None = None,
) -> None:
    """Inject materialized paths into env resolver and re-expand compose fields."""

    bootstrap.service_source_paths = dict(source_paths)
    bootstrap.set_env_resolver(
        inject_service_source_paths(
            bootstrap.env_resolver,
            source_paths,
        )
    )
    view = bootstrap.manifest_view
    if view is not None:
        bootstrap.set_manifest_view(
            refresh_manifest_view_compose_expansion(
                view,
                env_resolver=bootstrap.env_resolver,
            )
        )
    SymlinkManager(
        bootstrap, host_ctx=_symlink_host_view(bootstrap, host_ctx)
    ).sync_service_source_project_links(source_paths)
