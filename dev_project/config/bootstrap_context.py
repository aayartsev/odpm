"""Composition root for config bootstrap services (manifests, artifacts, defaults, transforms)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .artifacts import DeprecatedConfigHandler
from .defaults import ConfigDefaultsFactory
from .manifests import OdpmJsonReader, UserSettingsReader
from .manifests.odpm_json_writer import rewrite_odpm_json as write_odpm_json
from .transforms import OdooBuildDateResolver

if TYPE_CHECKING:
    from .config import Config


class ConfigBootstrapContext:
    def __init__(self, config: Config) -> None:
        self.config = config
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

    def rewrite_odpm_json(self) -> None:
        write_odpm_json(
            self.config,
            create_default=self.defaults.create_default_odpm_json_content,
        )
