from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..translations import _
from ..dependency_resolver import (
    DependencyDiscovery,
    DependencyResolutionResult,
    read_nested_odpm_fragment,
    read_oca_dependency_urls,
    resolve_dependencies,
)
from ..git import HandleOdooProjectLink
from ..logging import get_module_logger

if TYPE_CHECKING:
    from ..host.ports import BootstrapHandle

_logger = get_module_logger(__name__)
CheckoutFn = Callable[[HandleOdooProjectLink], None]


class DependencyMaterializer:
    def __init__(
        self,
        bootstrap: BootstrapHandle,
        *,
        checkout_fn: CheckoutFn,
    ) -> None:
        self.bootstrap = bootstrap
        self._checkout_fn = checkout_fn

    def resolve(self) -> DependencyResolutionResult:
        config = self.bootstrap
        seed_urls = list(config.project_settings.dependencies)
        if (
            config.skip_git_update()
            or not config.user_settings.use_oca_dependencies
        ):
            return DependencyResolutionResult(
                urls=seed_urls,
                nested_fragments=[],
            )

        # Read developing tree as-is: developer owns the branch/commit.
        # Full checkout belongs to ProjectLinks._should_checkout_developing
        # (explicit #branch/@commit, or CI/server lock pin) — not OCA discovery.
        initial_extra_urls: list[str] = []
        developing = self.bootstrap.developing_project
        if developing.project_path:
            initial_extra_urls = read_oca_dependency_urls(
                developing.project_path
            )

        return resolve_dependencies(
            seed_urls,
            self.discover_extensions,
            initial_extra_urls=initial_extra_urls,
        )

    def discover_extensions(self, dependency_string: str) -> DependencyDiscovery:
        bootstrap = self.bootstrap
        materialize = not bootstrap.skip_git_update()
        project = bootstrap.handle_git_link(
            dependency_string,
            materialize=materialize,
        )
        try:
            if not project.is_cloned:
                _logger.warning(
                    _(
                        "Git dependency {DEPENDENCY_URL} is not available locally; "
                        "transitive entries from oca_dependencies.txt and nested "
                        "odpm.json will be skipped"
                    ).format(DEPENDENCY_URL=dependency_string)
                )
                return DependencyDiscovery()
            self._checkout_fn(project)
            urls = read_oca_dependency_urls(project.project_path)
            nested = read_nested_odpm_fragment(
                project.project_path,
                resolver=bootstrap.env_resolver,
            )
            if nested is None:
                return DependencyDiscovery(urls=urls)
            merged_urls = list(urls)
            seen_urls = set(urls)
            for dependency_url in nested.dependencies:
                if dependency_url in seen_urls:
                    continue
                seen_urls.add(dependency_url)
                merged_urls.append(dependency_url)
            return DependencyDiscovery(
                urls=merged_urls,
                nested_fragment=nested,
            )
        finally:
            if project.project_path:
                bootstrap.ensure_git_repo_symlink(
                    project.project_path, scope="dependency"
                )

    def apply_to_config(self, resolution: DependencyResolutionResult) -> None:
        config = self.bootstrap
        config.project_settings.dependencies = resolution.urls
        if resolution.nested_fragments:
            self.bootstrap.apply_nested_compatibility(resolution.nested_fragments)
