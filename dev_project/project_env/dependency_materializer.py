from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .. import translations
from ..dependency_resolver import (
    DependencyDiscovery,
    DependencyResolutionResult,
    read_nested_odpm_fragment,
    read_oca_dependency_urls,
    resolve_dependencies,
)
from ..git import HandleOdooProjectLink
from ..inside_docker_app.logger import get_module_logger

if TYPE_CHECKING:
    from ..config.config import Config

_logger = get_module_logger(__name__)
CheckoutFn = Callable[[HandleOdooProjectLink], None]


class DependencyMaterializer:
    def __init__(
        self,
        config: Config,
        *,
        checkout_fn: CheckoutFn,
    ) -> None:
        self.config = config
        self._checkout_fn = checkout_fn

    def resolve(self) -> DependencyResolutionResult:
        seed_urls = list(self.config.dependencies)
        if self.config.skip_git_update() or not self.config.use_oca_dependencies:
            return DependencyResolutionResult(
                urls=seed_urls,
                transitive_requirements=[],
                nested_fragments=[],
            )

        initial_extra_urls: list[str] = []
        if self.config.developing_project.project_path:
            self._checkout_fn(self.config.developing_project)
            initial_extra_urls = read_oca_dependency_urls(
                self.config.developing_project.project_path
            )

        return resolve_dependencies(
            seed_urls,
            self.discover_extensions,
            initial_extra_urls=initial_extra_urls,
        )

    def discover_extensions(self, dependency_string: str) -> DependencyDiscovery:
        materialize = not self.config.skip_git_update()
        project = self.config.handle_git_link(
            dependency_string,
            materialize=materialize,
        )
        if not project.is_cloned:
            _logger.warning(
                translations.get_translation(
                    translations.OCA_DEPENDENCY_NOT_CLONED
                ).format(DEPENDENCY_URL=dependency_string)
            )
            return DependencyDiscovery()
        self._checkout_fn(project)
        urls = read_oca_dependency_urls(project.project_path)
        nested = read_nested_odpm_fragment(project.project_path)
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
            requirements=list(nested.requirements_txt),
            nested_fragment=nested,
        )

    def apply_to_config(self, resolution: DependencyResolutionResult) -> None:
        self.config.dependencies = resolution.urls
        if resolution.transitive_requirements or resolution.nested_fragments:
            self.config.apply_transitive_requirements(
                resolution.transitive_requirements,
                nested_fragments=resolution.nested_fragments,
            )
