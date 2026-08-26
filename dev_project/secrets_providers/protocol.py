"""SecretsProvider protocol."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from ..host.cli.args import OdpmCliArgs


class SecretsProvider(Protocol):
    """Fetch a flat schema-v1 secrets map. Must not write source files."""

    name: str

    def fetch(
        self,
        *,
        provider_config: Mapping[str, Any],
        credentials: Mapping[str, str],
        project_dir: str,
        arguments: OdpmCliArgs | None = None,
    ) -> dict[str, str]:
        ...
