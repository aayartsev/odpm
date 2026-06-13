"""Composition root for config bootstrap services."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .artifacts import DeprecatedConfigHandler
from .defaults import ConfigDefaultsFactory
from .git_repos import GitRepoCoordinator
from .manifests import OdpmJsonReader, UserSettingsReader
from .manifests.odpm_json_writer import rewrite_odpm_json as write_odpm_json
from .odoo_conf import OdooConfBuilder
from .paths import ConfigPaths
from .transforms import OdooBuildDateResolver

if TYPE_CHECKING:
    from .config import Config


class ConfigBootstrapContext:
    def __init__(
        self,
        config: Config,
        *,
        bind_platform_link: Callable[[Config], None] | None = None,
    ) -> None:
        self.config = config
        self._bind_platform_link = bind_platform_link
        self._wire_services()

    def _wire_services(self) -> None:
        self.defaults = ConfigDefaultsFactory(self.config)
        self.deprecated = DeprecatedConfigHandler(self.config)
        self.build_date = OdooBuildDateResolver(self.config)
        self.user_settings = UserSettingsReader(
            self.config,
            create_default_user_settings=self.defaults.create_default_user_setting_json_content,
        )
        self.odpm_json = OdpmJsonReader(
            self.config,
            rewrite_odpm_json=self.rewrite_odpm_json,
        )
        self.paths = ConfigPaths(self.config)
        self.odoo_conf = OdooConfBuilder(self.config)
        self.git_repos = GitRepoCoordinator(
            self.config,
            paths=self.paths,
            bind_platform_link=self._bind_platform_link,
        )

    def rewrite_odpm_json(self) -> None:
        write_odpm_json(
            self.config,
            create_default=self.defaults.create_default_odpm_json_content,
        )
