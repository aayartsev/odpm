"""Materialize manifest ``service_sources`` into ``ODOO_PROJECTS_DIR/service-sources/<name>``."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from ..errors import ConfigError, GitError
from ..logging import get_module_logger
from ..subprocess_runner import run_logged
from ..translations import _
from .runner import GitRunner

if TYPE_CHECKING:
    from ..config.config import Config
    from .deps_lock import LockEntry

_logger = get_module_logger(__name__)

SERVICE_SOURCES_DIR = "service-sources"


def service_source_target_dir(config: Config, name: str) -> str:
    """Absolute clone directory for a named service source."""
    return os.path.abspath(
        os.path.join(
            config.user_env.odoo_projects_dir,
            SERVICE_SOURCES_DIR,
            name,
        )
    )


def resolve_file_service_source_path(git_link: str) -> str:
    local = git_link.strip().replace("file://", "").strip().rstrip("/")
    if not local:
        raise ConfigError(
            _("service_sources file:// link must be a non-empty path.")
        )
    return os.path.abspath(local)


def materialize_service_sources(
    config: Config,
    *,
    lock_entries: dict[str, LockEntry] | None = None,
) -> dict[str, str]:
    """Clone or update service sources; return name → absolute host path."""
    view = config.bootstrap.manifest_view
    sources = view.service_sources if view is not None else None
    if not sources:
        return {}

    paths: dict[str, str] = {}
    for name, git_link in sorted(sources.items()):
        lock_entry = (lock_entries or {}).get(name)
        paths[name] = materialize_one_service_source(
            config,
            name,
            git_link,
            lock_entry=lock_entry,
        )
    return paths


def materialize_one_service_source(
    config: Config,
    name: str,
    git_link: str,
    *,
    lock_entry: LockEntry | None = None,
) -> str:
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

    base_root = os.path.join(config.user_env.odoo_projects_dir, SERVICE_SOURCES_DIR)
    os.makedirs(base_root, exist_ok=True)
    target = service_source_target_dir(config, name)

    project_link = config.handle_git_link(link, materialize=False)
    if lock_entry is not None and not link.startswith("file://"):
        from .deps_lock import apply_lock_entry_to_link

        apply_lock_entry_to_link(project_link, lock_entry)
    git_dir = os.path.join(target, ".git")
    if os.path.isdir(git_dir):
        project_link.project_path = target
        project_link.dir_to_clone = base_root
        project_link.check_project()
    else:
        if os.path.exists(target):
            shutil.rmtree(target)
        _clone_service_source_repo(project_link, target_dir=target, base_root=base_root)

    if project_link.branch and not config.skip_git_update():
        project_link.checkout_repository(
            str(config.odoo_version),
            clean_git_repos=config.user_settings.clean_git_repos,
            update_git_repos=config.user_settings.update_git_repos,
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


def collect_service_source_paths(config: Config) -> dict[str, str]:
    """Resolve current on-disk paths for effective ``service_sources``."""
    view = config.bootstrap.manifest_view
    sources = view.service_sources if view is not None else None
    if not sources:
        return {}
    paths: dict[str, str] = {}
    for name, git_link in sources.items():
        link = git_link.strip()
        if link.startswith("file://"):
            paths[name] = resolve_file_service_source_path(link)
        else:
            paths[name] = service_source_target_dir(config, name)
    return paths


def ensure_service_sources_present(config: Config) -> None:
    if not service_sources_need_materialize(config):
        return
    missing = []
    for name, path in collect_service_source_paths(config).items():
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
        target = os.path.abspath(
            os.path.join(odoo_projects_dir, SERVICE_SOURCES_DIR, name)
        )
        if not os.path.isdir(os.path.join(target, ".git")):
            return True
    return False


def service_sources_need_materialize(config: Config) -> bool:
    view = config.bootstrap.manifest_view
    return service_sources_need_materialize_for_view(
        manifest_view=view,
        odoo_projects_dir=config.user_env.odoo_projects_dir,
    )


def apply_materialized_service_sources(
    config: Config,
    source_paths: dict[str, str],
) -> None:
    """Inject materialized paths into env resolver and re-expand compose fields."""
    from ..config.transforms.env_substitution import inject_service_source_paths
    from ..manifest.reader import refresh_manifest_view_compose_expansion

    config.bootstrap.service_source_paths = dict(source_paths)
    config._env_resolver = inject_service_source_paths(
        config.env_resolver,
        source_paths,
    )
    view = config.bootstrap.manifest_view
    if view is not None:
        config.bootstrap.manifest_view = refresh_manifest_view_compose_expansion(
            view,
            env_resolver=config.env_resolver,
        )
